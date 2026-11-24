"""The asset creation engine (docs/asset-load.md section 3, docs/asset-engine.md).

    run(db, "hmda_lpc", transport="sample", dry_run=True)

One run reads one source and, for every record:

1. keeps the file as a snapshot, hashed, with personal fields removed first;
2. validates it: a polygon, in the right place (Telangana for real data, the open sea for the
   fictional samples), and accurate enough;
3. matches it to an asset: by this source's ID, by another department's ID it cites, or by
   overlap with an asset's current outline;
4. reconciles its boundary with the current one. It never lowers a boundary's status, and when
   two sources disagree at the same status it keeps the current boundary and reports a conflict;
5. publishes: a new asset, or a new boundary version (append-only), with the cohort following the
   status. Survey-number parcels are stored with land category and extent, and each asset's survey
   numbers are refreshed from the parcels it touches;
6. tags each asset with the document its record came from: the notification, the recovery order,
   the outline file or the land-record extract (DECISIONS.md D-057).

A dry run does all of this inside a savepoint and rolls it back, so the preview is exactly what an
applied run would do. Every applied run is recorded in `import_runs` with what it did to each
record.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import json
import re
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

import yaml
from geoalchemy2.elements import WKTElement
from shapely.geometry import box, mapping
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.audit import chain
from app.enums import BoundaryStatus
from app.models import Asset, AssetSourceLink, ImportRun, LandParcel, SourceSnapshot
from app.rules import config as rules
from app.services import boundaries as bsvc
from app.services import documents as doc_svc
from app.sources import connectors as registry
from app.sources import privacy
from app.sources.base import AssetRecord, Connector, Payload, SourceError
from app.sources.transports import FileDropTransport, OfficialApiTransport, SampleTransport
from app.storage import store

SETTINGS_FILE = Path(__file__).with_name("sources.yaml")

# Higher is stronger. A boundary is never replaced by a weaker one.
STATUS_RANK = {
    BoundaryStatus.physically_marked.value: 5,
    BoundaryStatus.final_notification.value: 4,
    BoundaryStatus.surveyed_agency.value: 4,
    BoundaryStatus.preliminary_notification.value: 3,
    BoundaryStatus.derived.value: 1,
    BoundaryStatus.survey_number_only.value: 0,
}

TRANSPORTS = ("file_drop", "sample", "api")
ACRE_SQ_M = 4046.8564224


@lru_cache(maxsize=1)
def settings() -> dict:
    return yaml.safe_load(SETTINGS_FILE.read_text(encoding="utf-8"))


def transport_for(name: str, kind: str):
    cfg = settings()
    if kind == "sample":
        return SampleTransport(name)
    if kind == "file_drop":
        return FileDropTransport(store.local_path(f"{cfg['drop_root']}/{name}"))
    if kind == "api":
        api = (cfg["connectors"].get(name) or {}).get("api") or {}
        return OfficialApiTransport(
            base_url=api.get("base_url"), agreement_ref=api.get("agreement_ref"),
            token_env=api.get("token_env"), paths=api.get("paths") or {},
        )
    raise SourceError(f"Unknown transport {kind!r}. Use one of: {', '.join(TRANSPORTS)}")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _link_id(external_id: str, is_sample: bool) -> str:
    # Sample IDs live in their own namespace, so a fictional record can never claim a real asset.
    return f"sample:{external_id}" if is_sample else external_id


def _natural(label: str) -> list:
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", label)]


class _Run:
    def __init__(self, db: Session, connector: Connector, transport_kind: str, actor_id: int | None, now: dt.datetime):
        self.db = db
        self.c = connector
        self.transport = transport_kind
        self.is_sample = transport_kind == "sample"
        self.actor_id = actor_id
        self.now = now
        self.cfg = settings()
        self.items: list[dict] = []
        self.counts: dict[str, int] = {}
        self.snapshots: dict[str, SourceSnapshot] = {}
        self.reused: set[str] = set()
        self.touched_assets: set[int] = set()
        self.parcel_assets: set[int] = set()
        bbox = self.cfg["sample_bbox"] if self.is_sample else self.cfg["real_bbox"]
        self.area = box(*bbox)
        self.area_name = "the open-sea sample area" if self.is_sample else "Telangana"

    def count(self, key: str, n: int = 1) -> None:
        self.counts[key] = self.counts.get(key, 0) + n

    def item(self, action: str, ref: str, **extra) -> None:
        self.items.append({"action": action, "ref": ref, **{k: v for k, v in extra.items() if v is not None}})

    # 1. Snapshots ------------------------------------------------------------------------

    def snapshot(self, payload: Payload, received_sha: str, stripped: list[str], dry_run: bool) -> SourceSnapshot:
        existing = self.db.scalar(select(SourceSnapshot).where(
            SourceSnapshot.connector == self.c.name, SourceSnapshot.dataset == payload.dataset,
            SourceSnapshot.received_sha256 == received_sha,
        ))
        if existing is not None:
            self.reused.add(payload.dataset)
            return existing
        stored_sha = sha256(payload.content).hexdigest()
        ext = Path(payload.file_name).suffix or ".bin"
        key = f"sources/{self.c.name}/{stored_sha}{ext}"
        if not dry_run:
            store.put_object(key, payload.content)
        snap = SourceSnapshot(
            connector=self.c.name, agency=self.c.agency, dataset=payload.dataset, transport=self.transport,
            file_name=payload.file_name, content_type=payload.content_type, received_sha256=received_sha,
            sha256=stored_sha, byte_size=len(payload.content), storage_key=key, source_date=payload.source_date,
            reference=payload.reference, agreement_ref=payload.agreement_ref,
            licence_note=self.c.licence_note + (" (fictional sample data)" if self.is_sample else ""),
            is_sample=self.is_sample, stripped_fields=stripped, received_by=self.actor_id,
        )
        self.db.add(snap)
        self.db.flush()
        return snap

    # 2. Validation -----------------------------------------------------------------------

    def check_geometry(self, geometry: dict | None, accuracy: float | None) -> str | None:
        """Why an outline cannot be loaded, or None if it can."""
        try:
            geom = bsvc.to_multipolygon(geometry or {})
        except bsvc.BoundaryError as exc:
            return str(exc)
        if not self.area.contains(geom):
            return f"outline lies outside {self.area_name}"
        if accuracy is not None and accuracy > float(self.cfg["max_positional_error_m"]):
            return f"positional error {accuracy:g} m is above the {self.cfg['max_positional_error_m']} m limit; georeference again"
        return None

    # 3. Matching -------------------------------------------------------------------------

    def _linked(self, connector: str, external_id: str) -> Asset | None:
        asset_id = self.db.scalar(select(AssetSourceLink.asset_id).where(
            AssetSourceLink.connector == connector,
            AssetSourceLink.external_id == _link_id(external_id, self.is_sample),
        ))
        return self.db.get(Asset, asset_id) if asset_id else None

    def _best_overlap(self, geometry: dict) -> tuple[int, float] | None:
        row = self.db.execute(text(
            """
            WITH g AS (SELECT ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326), 32644) AS m)
            SELECT a.id,
                   ST_Area(ST_Intersection(ST_Transform(b.geom, 32644), g.m))
                     / NULLIF(ST_Area(ST_Union(ST_Transform(b.geom, 32644), g.m)), 0) AS iou
            FROM assets a
            JOIN LATERAL (SELECT bv.geom FROM boundaries bv
                          WHERE bv.asset_id = a.id AND bv.kind IN ('ftl', 'parcel')
                          ORDER BY bv.version DESC LIMIT 1) b ON true
            CROSS JOIN g
            WHERE a.is_demo = :demo AND ST_Intersects(b.geom, ST_Transform(g.m, 4326))
            ORDER BY iou DESC NULLS LAST LIMIT 1
            """
        ), {"g": json.dumps(geometry), "demo": self.is_sample}).first()
        return (row[0], float(row[1] or 0)) if row else None

    def match(self, rec: AssetRecord) -> tuple[Asset | None, str | None, str | None]:
        """(asset, how it matched, conflict reason). A new link is needed unless matched by own ID."""
        asset = self._linked(self.c.name, rec.external_id)
        if asset is not None:
            return asset, "linked", None
        for other, other_id in rec.crosswalk.items():
            asset = self._linked(other, other_id)
            if asset is not None:
                return asset, "crosswalk", None
        if rec.boundary is not None:
            best = self._best_overlap(bsvc.to_multipolygon(rec.boundary.geometry).__geo_interface__)
            if best is not None:
                asset_id, iou = best
                if iou >= float(self.cfg["spatial_match_iou"]):
                    return self.db.get(Asset, asset_id), "spatial", None
                if iou >= float(self.cfg["spatial_conflict_iou"]):
                    other = self.db.get(Asset, asset_id)
                    return None, None, f"overlaps {other.asset_key} only partly (overlap {iou:.2f}); the boundary desk must decide"
        return None, None, None

    # 4. Reconciliation -------------------------------------------------------------------

    def _current_primary(self, asset_id: int) -> dict | None:
        row = self.db.execute(text(
            """
            SELECT b.id, b.kind::text AS kind, b.status::text AS status, b.valid_from, s.connector
            FROM boundaries b LEFT JOIN source_snapshots s ON s.id = b.source_snapshot_id
            WHERE b.asset_id = :a AND b.kind IN ('ftl', 'parcel')
            ORDER BY b.version DESC LIMIT 1
            """
        ), {"a": asset_id}).mappings().first()
        return dict(row) if row else None

    def _compare(self, boundary_id: int, geometry: dict) -> dict:
        row = self.db.execute(text(
            """
            WITH c AS (SELECT geom AS d, ST_Transform(geom, 32644) AS m FROM boundaries WHERE id = :i),
                 g AS (SELECT d, ST_Transform(d, 32644) AS m
                       FROM (SELECT ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326) AS d) x)
            SELECT ST_Equals(c.d, g.d) AS same,
                   ST_Area(ST_Intersection(c.m, g.m)) / NULLIF(ST_Area(ST_Union(c.m, g.m)), 0) AS iou,
                   ST_HausdorffDistance(c.m, g.m) AS max_offset_m,
                   (ST_Area(g.m) - ST_Area(c.m)) / NULLIF(ST_Area(c.m), 0) * 100 AS area_change_pct
            FROM c, g
            """
        ), {"i": boundary_id, "g": json.dumps(geometry)}).mappings().one()
        return {
            "same": bool(row["same"]),
            "iou": round(float(row["iou"] or 0), 3),
            "max_offset_m": round(float(row["max_offset_m"] or 0), 1),
            "area_change_pct": round(float(row["area_change_pct"] or 0), 1),
        }

    # 5. Publishing -----------------------------------------------------------------------

    def _add_link(self, asset: Asset, rec: AssetRecord, snap: SourceSnapshot, matched_by: str) -> None:
        self.db.add(AssetSourceLink(asset_id=asset.id, connector=self.c.name,
                                    external_id=_link_id(rec.external_id, self.is_sample),
                                    snapshot_id=snap.id, matched_by=matched_by))
        self.db.flush()
        self.count("links_added")

    def _add_version(self, asset: Asset, rec: AssetRecord, valid_from: dt.date) -> list:
        b = rec.boundary
        rows = bsvc.add_version(
            self.db, asset, kind=b.kind, status=b.status, geometry=b.geometry, source_name=b.source_name,
            source_url=b.source_url, source_date=b.source_date, notification_ref=b.notification_ref,
            certified_by=b.certified_by, valid_from=valid_from, actor_id=self.actor_id, at=self.now,
            source_snapshot_id=self.snapshots[b.dataset].id, positional_accuracy_m=b.positional_accuracy_m,
        )
        self._tag_boundary(asset, rec)
        return rows

    def _tag(self, asset: Asset, snap: SourceSnapshot, *, doc_type: str, title: str, reference: str | None,
             issued_on: dt.date | None = None, source_url: str | None = None) -> None:
        doc = doc_svc.tag_once(
            self.db, asset, doc_type=doc_type, title=title, reference=reference, source_snapshot_id=snap.id,
            issued_on=issued_on, issued_by=self.c.agency, source_url=source_url, file_key=snap.storage_key,
            file_sha256=snap.sha256, file_name=snap.file_name, content_type=snap.content_type,
            actor_id=self.actor_id, at=self.now,
        )
        if doc is not None:
            self.count("documents_tagged")

    def _tag_boundary(self, asset: Asset, rec: AssetRecord) -> None:
        """The document behind a boundary: its notification, its recovery order, or the outline file."""
        b = rec.boundary
        snap = self.snapshots[b.dataset]
        if b.status in (BoundaryStatus.final_notification.value, BoundaryStatus.preliminary_notification.value) and b.notification_ref:
            kind = "Final" if b.status == BoundaryStatus.final_notification.value else "Preliminary"
            self._tag(asset, snap, doc_type="notification", title=f"{kind} FTL notification {b.notification_ref}",
                      reference=b.notification_ref, issued_on=b.source_date, source_url=b.source_url)
        elif b.status == BoundaryStatus.physically_marked.value and b.notification_ref:
            self._tag(asset, snap, doc_type="recovery_order", title=f"Recovery order {b.notification_ref}",
                      reference=b.notification_ref, issued_on=b.source_date, source_url=b.source_url)
        else:
            self._tag(asset, snap, doc_type="survey_map", title=f"Outline from {self.c.agency}, not a notification",
                      reference=None, issued_on=b.source_date, source_url=b.source_url)

    def _fill_blanks(self, asset: Asset, rec: AssetRecord) -> list[str]:
        """Add what the asset lacks. Never overwrite another source's values."""
        changed = []
        for field in ("name_te", "district", "mandal", "village", "area_acres"):
            if getattr(asset, field) in (None, "") and getattr(rec, field) not in (None, ""):
                setattr(asset, field, getattr(rec, field))
                changed.append(field)
        merged = sorted(set(asset.survey_numbers or []) | set(rec.survey_numbers), key=_natural)
        if merged != list(asset.survey_numbers or []):
            asset.survey_numbers = merged
            changed.append("survey_numbers")
        return changed

    def asset(self, rec: AssetRecord) -> None:
        ref = f"{self.c.name}:{rec.external_id}"
        b = rec.boundary
        if b is None:
            self.count("waiting")
            self.item("waiting", ref, reason="no outline yet")
            return
        problem = self.check_geometry(b.geometry, b.positional_accuracy_m)
        if problem:
            self.count("rejected")
            self.item("rejected", ref, reason=problem)
            return
        asset, matched_by, conflict = self.match(rec)
        if conflict:
            self.count("conflicts")
            self.item("conflict", ref, reason=conflict)
            return
        snap = self.snapshots[rec.dataset]

        if asset is None:
            key = ("sample-" if self.is_sample else "") + f"{self.c.key_prefix}-{_slug(rec.external_id)}"
            if self.db.scalar(select(Asset.id).where(Asset.asset_key == key)):
                self.count("conflicts")
                self.item("conflict", ref, reason=f"asset key {key} is taken by an asset this source never linked")
                return
            asset = Asset(
                asset_key=key, name=rec.name, name_te=rec.name_te, type=rec.asset_type,
                cohort=rules.cohort_for_status(b.status).value, district=rec.district, mandal=rec.mandal,
                village=rec.village, survey_numbers=sorted(set(rec.survey_numbers), key=_natural),
                area_acres=rec.area_acres, custodian_agency=rec.custodian_agency, has_cctv=rec.has_cctv,
                baseline_date=rules.policy_cutoff_date(), is_demo=self.is_sample,
                notes=f"Created from {self.c.agency} ({self.transport}" + (", fictional sample)" if self.is_sample else ")"),
            )
            self.db.add(asset)
            self.db.flush()
            self._add_link(asset, rec, snap, "created")
            rows = self._add_version(asset, rec, b.source_date)
            chain.record(self.db, actor_id=self.actor_id, action="asset.created_from_source", entity="asset",
                         entity_id=asset.id, details={"connector": self.c.name, "external_id": rec.external_id,
                                                      "snapshot_id": snap.id, "boundary_version": rows[0].version},
                         at=self.now)
            self.touched_assets.add(asset.id)
            self.count("assets_created")
            self.item("created", ref, asset_id=asset.id, asset_key=asset.asset_key, cohort_after=asset.cohort,
                      status=b.status)
            return

        if asset.is_demo != self.is_sample:
            self.count("conflicts")
            self.item("conflict", ref, asset_key=asset.asset_key, reason="sample and real records never mix")
            return
        if matched_by != "linked":
            self._add_link(asset, rec, snap, matched_by)
        filled = self._fill_blanks(asset, rec)
        if filled:
            chain.record(self.db, actor_id=self.actor_id, action="asset.filled_from_source", entity="asset",
                         entity_id=asset.id, details={"connector": self.c.name, "fields": filled}, at=self.now)
            self.touched_assets.add(asset.id)

        current = self._current_primary(asset.id)
        common = {"asset_id": asset.id, "asset_key": asset.asset_key, "matched_by": matched_by,
                  "filled": filled or None}
        if current is None:
            self._add_version(asset, rec, b.source_date)
            self.touched_assets.add(asset.id)
            self.count("boundary_versions")
            self.item("new_version", ref, status=b.status, cohort_after=asset.cohort, **common)
            return
        if current["kind"] != b.kind:
            self.count("conflicts")
            self.item("conflict", ref, reason=f"source gives a {b.kind} outline; the asset has a {current['kind']}", **common)
            return
        metrics = self._compare(current["id"], bsvc.to_multipolygon(b.geometry).__geo_interface__)
        same_geom = metrics.pop("same")
        rank_in, rank_cur = STATUS_RANK[b.status], STATUS_RANK[current["status"]]
        if same_geom and b.status == current["status"]:
            self.count("unchanged")
            self.item("unchanged", ref, status=b.status, **common)
            return
        if rank_in < rank_cur:
            self.count("skipped_weaker")
            self.item("skipped_weaker", ref, metrics=metrics,
                      reason=f"kept the current {current['status']} boundary; this source gives {b.status}", **common)
            return
        if rank_in == rank_cur and current["connector"] != self.c.name:
            self.count("conflicts")
            self.item("conflict", ref, metrics=metrics,
                      reason=f"another source gives a different {current['status']} outline; the current one is kept "
                             "until the boundary desk decides", **common)
            return
        cohort_before = asset.cohort
        self._add_version(asset, rec, max(b.source_date, current["valid_from"]))
        self.touched_assets.add(asset.id)
        self.count("boundary_versions")
        self.item("new_version", ref, status=b.status, status_before=current["status"], cohort_before=cohort_before,
                  cohort_after=asset.cohort, metrics=metrics, **common)

    def parcels(self, parsed_parcels: list) -> None:
        if not parsed_parcels:
            return
        snap = self.snapshots[parsed_parcels[0].dataset]
        if parsed_parcels[0].dataset in self.reused:
            self.count("parcels_unchanged", len(parsed_parcels))
            self.item("parcels", f"{self.c.name}:{snap.file_name}", reason="this file was loaded before; parcels unchanged")
            return
        loaded = 0
        for p in parsed_parcels:
            problem = self.check_geometry(p.geometry, p.positional_accuracy_m)
            if problem:
                self.count("rejected")
                self.item("rejected", f"{self.c.name}:{p.village}/{p.label}", reason=problem)
                continue
            geom = bsvc.to_multipolygon(p.geometry)
            self.db.add(LandParcel(
                snapshot_id=snap.id, district=p.district, mandal=p.mandal, village=p.village, survey_no=p.survey_no,
                sub_division=p.sub_division, bhudhaar=p.bhudhaar, land_category=p.land_category,
                recorded_category=p.recorded_category, extent_acres=p.extent_acres,
                positional_accuracy_m=p.positional_accuracy_m, geom=WKTElement(geom.wkt, srid=4326),
                is_sample=self.is_sample,
            ))
            loaded += 1
        self.db.flush()
        self.count("parcels_loaded", loaded)
        self.item("parcels", f"{self.c.name}:{snap.file_name}", reason=f"{loaded} survey-number parcels loaded")
        limit = float(self.cfg["extent_mismatch_pct"])
        for row in self.db.execute(text(
            """
            SELECT village, survey_no, sub_division, extent_acres,
                   ST_Area(ST_Transform(geom, 32644)) / :acre AS drawn_acres
            FROM land_parcels WHERE snapshot_id = :s AND extent_acres > 0
            """
        ), {"s": snap.id, "acre": ACRE_SQ_M}).mappings():
            diff = (float(row["drawn_acres"]) - float(row["extent_acres"])) / float(row["extent_acres"]) * 100
            if abs(diff) > limit:
                label = row["survey_no"] + (f"/{row['sub_division']}" if row["sub_division"] else "")
                self.count("warnings")
                self.item("warning", f"{self.c.name}:{row['village']}/{label}",
                          reason=f"drawn area differs from the recorded extent by {diff:+.0f}%")
        # Every asset these parcels touch gets its survey numbers refreshed and its land records tagged.
        self.parcel_assets = set(self.db.scalars(text(
            """
            SELECT DISTINCT b.asset_id FROM boundaries b JOIN assets a ON a.id = b.asset_id
            WHERE a.is_demo = :demo AND b.kind IN ('ftl', 'parcel', 'buffer')
              AND ST_Intersects(b.geom, (SELECT ST_Union(geom) FROM land_parcels WHERE snapshot_id = :s))
            """
        ), {"demo": self.is_sample, "s": snap.id}))
        self.touched_assets |= self.parcel_assets

    def tag_land_records(self) -> None:
        """Each asset the new parcels touch carries the village map and the Record of Rights extract."""
        for asset_id in sorted(self.parcel_assets):
            asset = self.db.get(Asset, asset_id)
            for snap in self.snapshots.values():
                if snap.dataset == "ror":
                    self._tag(asset, snap, doc_type="land_record", title="Record of Rights extract (land category and extent, no names)",
                              reference=None, issued_on=snap.source_date)
                elif snap.dataset == "parcels":
                    self._tag(asset, snap, doc_type="survey_map", title="Village cadastral map (survey-number parcels)",
                              reference=None, issued_on=snap.source_date)

    def refresh_survey_numbers(self) -> None:
        for asset_id in sorted(self.touched_assets):
            asset = self.db.get(Asset, asset_id)
            found = self.db.execute(text(
                """
                WITH zone AS (
                    SELECT ST_Union(b.geom) AS g FROM boundaries b
                    WHERE b.asset_id = :a AND b.kind IN ('ftl', 'parcel', 'buffer')
                      AND b.version = (SELECT max(version) FROM boundaries WHERE asset_id = :a))
                SELECT DISTINCT p.survey_no, p.sub_division FROM land_parcels_current p, zone
                WHERE p.is_sample = :demo AND ST_Intersects(p.geom, zone.g) AND NOT ST_Touches(p.geom, zone.g)
                """
            ), {"a": asset_id, "demo": asset.is_demo}).all()
            labels = {f"{s}/{d}" if d else s for s, d in found}
            merged = sorted(set(asset.survey_numbers or []) | labels, key=_natural)
            if merged != list(asset.survey_numbers or []):
                added = sorted(set(merged) - set(asset.survey_numbers or []), key=_natural)
                asset.survey_numbers = merged
                chain.record(self.db, actor_id=self.actor_id, action="asset.survey_numbers_from_parcels", entity="asset",
                             entity_id=asset.id, details={"added": added, "connector": self.c.name}, at=self.now)
                self.count("survey_numbers_updated")
                self.item("survey_numbers", f"asset:{asset.asset_key}", asset_id=asset.id, asset_key=asset.asset_key,
                          reason=f"added {', '.join(added)} from the parcels it touches")


def run(
    db: Session,
    connector_name: str,
    *,
    transport: str = "file_drop",
    dry_run: bool = True,
    actor_id: int | None = None,
    now: dt.datetime | None = None,
    transport_obj=None,
) -> dict:
    """Read one source and create or update assets from it. Dry run by default."""
    connector = registry.get(connector_name)
    if transport not in TRANSPORTS:
        raise SourceError(f"Unknown transport {transport!r}. Use one of: {', '.join(TRANSPORTS)}")
    t = transport_obj or transport_for(connector.name, transport)
    started = now or dt.datetime.now(dt.timezone.utc)
    payloads = t.fetch(connector)

    clean: dict[str, Payload] = {}
    received: dict[str, tuple[str, list[str]]] = {}
    for name, payload in payloads.items():
        fmt = connector.spec(name).format
        received_sha = sha256(payload.content).hexdigest()
        content, stripped = privacy.sanitise(payload.content, fmt)
        clean[name] = dataclasses.replace(payload, content=content)
        received[name] = (received_sha, stripped)
    parsed = connector.parse(clean)

    r = _Run(db, connector, t.kind, actor_id, started)
    savepoint = db.begin_nested() if dry_run else None
    try:
        for name, payload in clean.items():
            r.snapshots[name] = r.snapshot(payload, *received[name], dry_run=dry_run)
            if received[name][1]:
                r.item("privacy", f"{connector.name}:{payload.file_name}",
                       reason=f"removed personal field(s) before storing: {', '.join(received[name][1])}")
        for entry in parsed.rejected:
            r.count("rejected")
            r.item("rejected", entry["ref"], reason=entry["reason"])
        for entry in parsed.waiting:
            r.count("waiting")
            r.item("waiting", entry["ref"], reason=entry["reason"])
        for entry in parsed.warnings:
            r.count("warnings")
            r.item("warning", entry["ref"], reason=entry["reason"])
        for rec in parsed.assets:
            r.asset(rec)
        r.parcels(parsed.parcels)
        r.refresh_survey_numbers()
        r.tag_land_records()

        finished = max(dt.datetime.now(dt.timezone.utc), started)
        report = {
            "connector": connector.name,
            "agency": connector.agency,
            "transport": t.kind,
            "is_sample": r.is_sample,
            "dry_run": dry_run,
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "snapshots": [
                {"id": None if dry_run else s.id, "dataset": s.dataset, "file_name": s.file_name, "sha256": s.sha256,
                 "received_sha256": s.received_sha256, "source_date": s.source_date.isoformat(),
                 "stripped_fields": list(s.stripped_fields or []), "reused": s.dataset in r.reused}
                for s in r.snapshots.values()
            ],
            "counts": dict(sorted(r.counts.items())),
            "items": r.items,
        }
        if dry_run:
            report["run_id"] = None
            for entry in report["items"]:
                entry.pop("asset_id", None)  # IDs of rows that are rolled back mean nothing
        else:
            row = ImportRun(connector=connector.name, transport=t.kind, is_sample=r.is_sample, started_at=started,
                            finished_at=finished, actor_id=actor_id, snapshot_ids=[s.id for s in r.snapshots.values()],
                            counts=report["counts"], items=r.items)
            db.add(row)
            db.flush()
            chain.record(db, actor_id=actor_id, action="sources.import_run", entity="import_run", entity_id=row.id,
                         details={"connector": connector.name, "transport": t.kind, "counts": report["counts"]},
                         at=started)
            report["run_id"] = row.id
    except Exception:
        if savepoint is not None and savepoint.is_active:
            savepoint.rollback()
        raise
    if savepoint is not None:
        savepoint.rollback()
    else:
        db.commit()
    return report
