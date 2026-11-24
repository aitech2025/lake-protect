"""Template connectors for the four government sources in docs/asset-load.md section 7.

Each connector states its data contract (the files and fields it expects) and reads those files
into records. None of them calls a government system: until a data-sharing agreement exists the
files come from a drop folder or from the fictional samples. When an agreement fixes the real
field names, only the field mapping in the connector changes.

Status rules, applied here and nowhere else:
- Only the Lake Protection Committee's notification gives a lake boundary a notified status, and
  a notified boundary must cite its notification (reference and date). Otherwise it is refused.
- An Irrigation outline is not a notification: it loads as `derived` (watch only).
- A HYDRAA recovered parcel is `physically_marked` only with its order reference and marking date.
"""
from __future__ import annotations

from app.enums import AssetType, BoundaryStatus
from app.sources.base import (
    AssetRecord,
    BoundaryRecord,
    Connector,
    DatasetSpec,
    ParcelRecord,
    Parsed,
    Payload,
    SourceError,
    as_date,
    as_float,
    read_csv,
    read_geojson,
    split_list,
)

HA_TO_ACRES = 2.4710538

NOTIFIED = {
    "final": BoundaryStatus.final_notification.value,
    "preliminary": BoundaryStatus.preliminary_notification.value,
}


def _notified_boundary(ref_label: str, status_raw: str, ref: str, date_raw: str, rejected: list) -> tuple[str, object] | None:
    """Status and date for a notified lake, or None after recording why it was refused."""
    status_raw = (status_raw or "").strip().lower()
    if status_raw in ("", "none", "not_notified"):
        return BoundaryStatus.derived.value, None
    if status_raw not in NOTIFIED:
        rejected.append({"ref": ref_label, "reason": f"unknown notification status {status_raw!r} (use final, preliminary or none)"})
        return None
    if not ref or not date_raw:
        rejected.append({"ref": ref_label, "reason": f"a {status_raw} notification must cite its reference and date"})
        return None
    try:
        return NOTIFIED[status_raw], as_date(date_raw, f"{ref_label} notification_date")
    except SourceError as exc:
        rejected.append({"ref": ref_label, "reason": str(exc)})
        return None


def _survey_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return split_list(value)


class HmdaLpc(Connector):
    name = "hmda_lpc"
    agency = "HMDA Lake Protection Committee"
    key_prefix = "lpc"
    summary = "Lake register and FTL outlines, with each lake's notification status"
    licence_note = "Government of Telangana data, shared for the State's lake watch only"
    datasets = (
        DatasetSpec(
            "lakes", "lakes.csv", "csv", True,
            ("lake_id", "lake_name", "district", "mandal", "village", "survey_numbers", "area_ha", "notification_status"),
            "One row per lake. notification_status is final, preliminary or none. survey_numbers are separated by ';'",
            ("lake_name_te", "notification_ref", "notification_date", "notification_url", "certified_by", "positional_accuracy_m"),
        ),
        DatasetSpec(
            "ftl", "ftl.geojson", "geojson", True, ("lake_id",),
            "FTL outline per lake (Polygon or MultiPolygon, WGS 84)",
            ("positional_accuracy_m", "method"),
        ),
    )

    def parse(self, payloads: dict[str, Payload]) -> Parsed:
        self.check_present(payloads)
        out = Parsed()
        rows = read_csv(payloads["lakes"], self.spec("lakes"))
        outlines: dict[str, dict] = {}
        for f in read_geojson(payloads["ftl"], self.spec("ftl")):
            outlines.setdefault(str(f["properties"]["lake_id"]).strip(), f)
        seen: set[str] = set()
        for row in rows:
            lake_id = row["lake_id"]
            ref_label = f"{self.name}:{lake_id}"
            if not lake_id or lake_id in seen:
                out.rejected.append({"ref": ref_label, "reason": "missing or repeated lake_id"})
                continue
            seen.add(lake_id)
            decided = _notified_boundary(ref_label, row["notification_status"], row.get("notification_ref", ""),
                                         row.get("notification_date", ""), out.rejected)
            if decided is None:
                continue
            status, notified_on = decided
            area_ha = as_float(row["area_ha"])
            record = AssetRecord(
                external_id=lake_id,
                name=row["lake_name"],
                name_te=row.get("lake_name_te") or None,
                asset_type=AssetType.lake.value,
                custodian_agency="HMDA",
                district=row["district"] or None,
                mandal=row["mandal"] or None,
                village=row["village"] or None,
                survey_numbers=split_list(row["survey_numbers"]),
                area_acres=round(area_ha * HA_TO_ACRES, 3) if area_ha is not None else None,
                dataset="lakes",
            )
            feature = outlines.get(lake_id)
            if feature is None:
                out.waiting.append({"ref": ref_label, "reason": "no FTL outline in ftl.geojson yet"})
                continue
            props = feature.get("properties") or {}
            notified = status != BoundaryStatus.derived.value
            record.boundary = BoundaryRecord(
                kind="ftl",
                status=status,
                geometry=feature.get("geometry"),
                source_name=(
                    f"{self.agency}: {row['notification_status'].lower()} notification {row['notification_ref']}"
                    if notified else f"{self.agency}: register outline, not notified"
                ),
                source_date=notified_on or payloads["ftl"].source_date,
                source_url=row.get("notification_url") or None,
                notification_ref=row.get("notification_ref") or None,
                certified_by=row.get("certified_by") or None,
                positional_accuracy_m=as_float(props.get("positional_accuracy_m", row.get("positional_accuracy_m"))),
                dataset="ftl",
            )
            out.assets.append(record)
        for lake_id in sorted(set(outlines) - seen):
            out.warnings.append({"ref": f"{self.name}:{lake_id}", "reason": "outline in ftl.geojson has no row in lakes.csv"})
        return out


class Irrigation(Connector):
    name = "irrigation"
    agency = "Irrigation and CAD Department"
    key_prefix = "mi"
    summary = "Minor irrigation tank inventory and surveyed tank outlines (not notifications)"
    licence_note = "Government of Telangana data, shared for the State's lake watch only"
    datasets = (
        DatasetSpec(
            "tanks", "tanks.csv", "csv", True,
            ("tank_id", "tank_name", "district", "mandal", "village"),
            "One row per tank from the minor irrigation census. hmda_lake_id links the tank to the LPC register",
            ("tank_name_te", "hmda_lake_id", "survey_numbers", "ftl_level_m", "weir_crest_m", "surveyed_by"),
        ),
        DatasetSpec(
            "outlines", "tank_outlines.geojson", "geojson", False, ("tank_id",),
            "Surveyed or digitised tank outline, with how it was made",
            ("method", "positional_accuracy_m", "survey_date"),
        ),
    )

    def parse(self, payloads: dict[str, Payload]) -> Parsed:
        self.check_present(payloads)
        out = Parsed()
        outlines: dict[str, dict] = {}
        if "outlines" in payloads:
            for f in read_geojson(payloads["outlines"], self.spec("outlines")):
                outlines.setdefault(str(f["properties"]["tank_id"]).strip(), f)
        for row in read_csv(payloads["tanks"], self.spec("tanks")):
            tank_id = row["tank_id"]
            ref_label = f"{self.name}:{tank_id}"
            record = AssetRecord(
                external_id=tank_id,
                name=row["tank_name"],
                name_te=row.get("tank_name_te") or None,
                asset_type=AssetType.lake.value,
                custodian_agency="Irrigation and CAD",
                district=row["district"] or None,
                mandal=row["mandal"] or None,
                village=row["village"] or None,
                survey_numbers=split_list(row.get("survey_numbers")),
                crosswalk={"hmda_lpc": row["hmda_lake_id"]} if row.get("hmda_lake_id") else {},
                dataset="tanks",
            )
            feature = outlines.get(tank_id)
            if feature is None:
                out.waiting.append({"ref": ref_label, "reason": "no outline in tank_outlines.geojson yet"})
                continue
            props = feature.get("properties") or {}
            method = props.get("method") or "method not stated"
            try:
                surveyed_on = as_date(props["survey_date"], f"{ref_label} survey_date") if props.get("survey_date") else payloads["outlines"].source_date
            except SourceError as exc:
                out.rejected.append({"ref": ref_label, "reason": str(exc)})
                continue
            record.boundary = BoundaryRecord(
                kind="ftl",
                status=BoundaryStatus.derived.value,  # an Irrigation outline is not a notification
                geometry=feature.get("geometry"),
                source_name=f"{self.agency}: tank outline ({method}), not notified",
                source_date=surveyed_on,
                certified_by=row.get("surveyed_by") or None,
                positional_accuracy_m=as_float(props.get("positional_accuracy_m")),
                dataset="outlines",
            )
            out.assets.append(record)
        return out


# Record of Rights land classification, as written, to the register's land categories.
LAND_CATEGORY = {
    "sarkari": "government", "government": "government", "poramboke": "government", "govt": "government",
    "kunta": "tank", "cheruvu": "tank", "tank": "tank", "tank bed": "tank",
    "shikam": "shikam", "sarkari shikam": "shikam",
    "patta": "patta", "private": "patta",
    "assigned": "assigned", "lavani patta": "assigned",
    "inam": "inam",
    "endowment": "endowment", "devadaya": "endowment",
    "wakf": "wakf",
    "forest": "forest", "aranya": "forest",
}


class BhuBharati(Connector):
    name = "bhu_bharati"
    agency = "CCLA, Survey Settlement and Land Records (Bhu Bharati)"
    key_prefix = "ror"
    summary = "Village cadastral parcels joined to the Record of Rights land classification, without owner names"
    licence_note = "Government of Telangana land records, shared for the State's lake watch only; no personal data"
    datasets = (
        DatasetSpec(
            "parcels", "village_parcels.geojson", "geojson", True,
            ("district", "mandal", "village", "survey_no"),
            "Survey-number polygons for each village a lake touches (WGS 84)",
            ("sub_division", "positional_accuracy_m"),
        ),
        DatasetSpec(
            "ror", "ror_extract.csv", "csv", True,
            ("district", "mandal", "village", "survey_no", "land_classification", "extent_acres"),
            "Record of Rights extract: classification and extent per survey number. Names are removed on arrival",
            ("sub_division", "bhudhaar"),
        ),
    )

    @staticmethod
    def _key(d: dict) -> tuple[str, str, str, str, str]:
        return tuple(str(d.get(k) or "").strip() for k in ("district", "mandal", "village", "survey_no", "sub_division"))  # type: ignore[return-value]

    def parse(self, payloads: dict[str, Payload]) -> Parsed:
        self.check_present(payloads)
        out = Parsed()
        ror: dict[tuple, dict] = {}
        for row in read_csv(payloads["ror"], self.spec("ror")):
            ror.setdefault(self._key(row), row)
        drawn: set[tuple] = set()
        for f in read_geojson(payloads["parcels"], self.spec("parcels")):
            props = f.get("properties") or {}
            key = self._key(props)
            label = f"{self.name}:{'/'.join(k for k in key if k)}"
            if key in drawn:
                out.rejected.append({"ref": label, "reason": "survey number drawn twice in village_parcels.geojson"})
                continue
            drawn.add(key)
            record_row = ror.get(key)
            recorded = (record_row or {}).get("land_classification", "")
            category = LAND_CATEGORY.get(recorded.strip().lower(), "unknown")
            if record_row is None:
                out.warnings.append({"ref": label, "reason": "no Record of Rights row; land category unknown"})
            elif category == "unknown":
                out.warnings.append({"ref": label, "reason": f"land classification {recorded!r} not recognised"})
            out.parcels.append(ParcelRecord(
                district=key[0], mandal=key[1], village=key[2], survey_no=key[3], sub_division=key[4],
                land_category=category,
                recorded_category=recorded or None,
                bhudhaar=(record_row or {}).get("bhudhaar") or None,
                extent_acres=as_float((record_row or {}).get("extent_acres")),
                geometry=f.get("geometry"),
                positional_accuracy_m=as_float(props.get("positional_accuracy_m")),
                dataset="parcels",
            ))
        for key in sorted(set(ror) - drawn):
            out.rejected.append({"ref": f"{self.name}:{'/'.join(k for k in key if k)}", "reason": "Record of Rights row with no polygon"})
        return out


class Hydraa(Connector):
    name = "hydraa"
    agency = "HYDRAA (HYDRAA-Raksha layers and recovered land)"
    key_prefix = "hydraa"
    summary = "FTL layer as notified, and recovered parcels physically marked on the ground"
    licence_note = "Government of Telangana data, shared for the State's lake watch only"
    datasets = (
        DatasetSpec(
            "ftl_layer", "ftl_layer.geojson", "geojson", False,
            ("hmda_lake_id", "lake_name", "status"),
            "FTL outlines from HYDRAA-Raksha. status is final, preliminary or none",
            ("lake_ref", "notification_ref", "notification_date", "positional_accuracy_m"),
        ),
        DatasetSpec(
            "recovered", "recovered_parcels.geojson", "geojson", False,
            ("parcel_ref", "name", "district", "mandal", "village", "marked_on", "order_ref"),
            "Recovered land, physically marked, with the order that recovered it",
            ("name_te", "survey_numbers", "recovered_on", "positional_accuracy_m"),
        ),
    )

    def parse(self, payloads: dict[str, Payload]) -> Parsed:
        self.check_present(payloads)
        out = Parsed()
        if "ftl_layer" in payloads:
            for f in read_geojson(payloads["ftl_layer"], self.spec("ftl_layer")):
                p = f.get("properties") or {}
                hmda_id = str(p["hmda_lake_id"]).strip()
                external_id = str(p.get("lake_ref") or f"ftl-{hmda_id}").strip()
                ref_label = f"{self.name}:{external_id}"
                decided = _notified_boundary(ref_label, p.get("status", ""), str(p.get("notification_ref") or ""),
                                             str(p.get("notification_date") or ""), out.rejected)
                if decided is None:
                    continue
                status, notified_on = decided
                out.assets.append(AssetRecord(
                    external_id=external_id,
                    name=p["lake_name"],
                    asset_type=AssetType.lake.value,
                    custodian_agency="HMDA",
                    crosswalk={"hmda_lpc": hmda_id} if hmda_id else {},
                    boundary=BoundaryRecord(
                        kind="ftl",
                        status=status,
                        geometry=f.get("geometry"),
                        source_name=(f"HYDRAA-Raksha FTL layer: {p['status']} notification {p.get('notification_ref')}"
                                     if notified_on else "HYDRAA-Raksha FTL layer, not notified"),
                        source_date=notified_on or payloads["ftl_layer"].source_date,
                        notification_ref=p.get("notification_ref") or None,
                        positional_accuracy_m=as_float(p.get("positional_accuracy_m")),
                        dataset="ftl_layer",
                    ),
                    dataset="ftl_layer",
                ))
        if "recovered" in payloads:
            for f in read_geojson(payloads["recovered"], self.spec("recovered")):
                p = f.get("properties") or {}
                ref_label = f"{self.name}:{p['parcel_ref']}"
                if not p.get("order_ref") or not p.get("marked_on"):
                    out.rejected.append({"ref": ref_label, "reason": "a recovered parcel needs its order reference and marking date"})
                    continue
                try:
                    marked_on = as_date(p["marked_on"], f"{ref_label} marked_on")
                except SourceError as exc:
                    out.rejected.append({"ref": ref_label, "reason": str(exc)})
                    continue
                out.assets.append(AssetRecord(
                    external_id=str(p["parcel_ref"]).strip(),
                    name=p["name"],
                    name_te=p.get("name_te") or None,
                    asset_type=AssetType.recovered_parcel.value,
                    custodian_agency="HYDRAA",
                    district=p.get("district") or None,
                    mandal=p.get("mandal") or None,
                    village=p.get("village") or None,
                    survey_numbers=_survey_list(p.get("survey_numbers")),
                    boundary=BoundaryRecord(
                        kind="parcel",
                        status=BoundaryStatus.physically_marked.value,
                        geometry=f.get("geometry"),
                        source_name=f"HYDRAA: recovered and marked under order {p['order_ref']}",
                        source_date=marked_on,
                        notification_ref=str(p["order_ref"]),
                        certified_by="HYDRAA",
                        positional_accuracy_m=as_float(p.get("positional_accuracy_m")),
                        dataset="recovered",
                    ),
                    dataset="recovered",
                ))
        return out


CONNECTORS: dict[str, Connector] = {c.name: c for c in (HmdaLpc(), Irrigation(), BhuBharati(), Hydraa())}


def get(name: str) -> Connector:
    try:
        return CONNECTORS[name]
    except KeyError as exc:
        raise SourceError(f"Unknown source {name!r}. Known: {', '.join(CONNECTORS)}") from exc
