"""Boundary versions (CONTEXT.md sections 4, 6.1, 7, 8.3).

A boundary version is a set of rows for one asset: the defined boundary (FTL or parcel), a
buffer derived from it at the configured width, and a 100 m watch ring. A change is always a new
version. Old versions stay retrievable through the `boundary_versions` view.
"""
from __future__ import annotations

import datetime as dt

from geoalchemy2.elements import WKTElement
from shapely.geometry import MultiPolygon, shape
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.audit import chain
from app.enums import BoundaryKind
from app.models import Asset, Boundary
from app.rules import config as rules

PRIMARY_KINDS = {BoundaryKind.ftl.value, BoundaryKind.parcel.value}

_DERIVE_SQL = text(
    """
    INSERT INTO boundaries (asset_id, version, kind, status, geom, source_name, source_url, source_date,
                            notification_ref, certified_by, valid_from, valid_to, supersedes_id,
                            derived_from_id, sha256)
    SELECT p.asset_id, p.version, CAST(:kind AS boundary_kind), p.status,
           ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_Transform(
               ST_Difference(ST_Buffer(ST_Transform(p.geom, 32644), :outer_m),
                             CASE WHEN :inner_m > 0 THEN ST_Buffer(ST_Transform(p.geom, 32644), :inner_m)
                                  ELSE ST_Transform(p.geom, 32644) END),
               4326)), 3)),
           :source_name, p.source_url, p.source_date, p.notification_ref, p.certified_by,
           p.valid_from, p.valid_to, :supersedes_id, p.id, ''
    FROM boundaries p WHERE p.id = :primary_id
    RETURNING id
    """
)


class BoundaryError(ValueError):
    pass


def to_multipolygon(geometry: dict) -> MultiPolygon:
    try:
        geom = shape(geometry)
    except Exception as exc:  # noqa: BLE001
        raise BoundaryError(f"Not a GeoJSON geometry: {exc}") from exc
    if geom.geom_type == "Polygon":
        geom = MultiPolygon([geom])
    if geom.geom_type != "MultiPolygon":
        raise BoundaryError(f"Boundary must be a Polygon or MultiPolygon, got {geom.geom_type}")
    if geom.is_empty or not geom.is_valid:
        raise BoundaryError("Boundary geometry is empty or invalid")
    return geom


def _latest_of_kind(db: Session, asset_id: int, kind: str, below_version: int) -> int | None:
    return db.scalar(
        select(Boundary.id)
        .where(Boundary.asset_id == asset_id, Boundary.kind == kind, Boundary.version < below_version)
        .order_by(Boundary.version.desc())
        .limit(1)
    )


def add_version(
    db: Session,
    asset: Asset,
    *,
    kind: str,
    status: str,
    geometry: dict,
    source_name: str,
    source_url: str | None = None,
    source_date: dt.date | None = None,
    notification_ref: str | None = None,
    certified_by: str | None = None,
    valid_from: dt.date | None = None,
    actor_id: int | None = None,
    at: dt.datetime | None = None,
) -> list[Boundary]:
    """Insert a new boundary version with its derived buffer and watch ring. Moves the asset's cohort."""
    if kind not in PRIMARY_KINDS:
        raise BoundaryError("Post an ftl or parcel boundary. Buffer and watch ring are derived from it.")
    geom = to_multipolygon(geometry)
    version = (db.scalar(select(func.max(Boundary.version)).where(Boundary.asset_id == asset.id)) or 0) + 1
    primary = Boundary(
        asset_id=asset.id,
        version=version,
        kind=kind,
        status=status,
        geom=WKTElement(geom.wkt, srid=4326),
        source_name=source_name,
        source_url=source_url,
        source_date=source_date,
        notification_ref=notification_ref,
        certified_by=certified_by,
        valid_from=valid_from or dt.date.today(),
        supersedes_id=_latest_of_kind(db, asset.id, kind, version),
        sha256="",
    )
    db.add(primary)
    db.flush()

    rv = rules.rule_version()
    ring = rules.watch_ring_m()
    derived_specs: list[tuple[str, float, float, str]] = []
    if kind == BoundaryKind.ftl.value:
        area_ha = db.scalar(text("SELECT ST_Area(ST_Transform(geom, 32644)) / 10000 FROM boundaries WHERE id = :i"), {"i": primary.id})
        width = rules.lake_buffer_width_m(float(area_ha))
        derived_specs.append(("buffer", width, 0.0, f"Derived from boundary {primary.id}: {width:g} m buffer ({rv})"))
        derived_specs.append(("watch_ring", width + ring, width, f"Derived from boundary {primary.id}: {ring:g} m watch ring beyond the buffer ({rv})"))
    else:
        derived_specs.append(("watch_ring", ring, 0.0, f"Derived from boundary {primary.id}: {ring:g} m watch ring ({rv})"))

    created_ids = [primary.id]
    for dkind, outer_m, inner_m, label in derived_specs:
        new_id = db.execute(
            _DERIVE_SQL,
            {
                "kind": dkind,
                "outer_m": outer_m,
                "inner_m": inner_m,
                "source_name": label,
                "supersedes_id": _latest_of_kind(db, asset.id, dkind, version),
                "primary_id": primary.id,
            },
        ).scalar_one()
        created_ids.append(new_id)

    new_cohort = rules.cohort_for_status(status).value
    old_cohort = asset.cohort
    if new_cohort != old_cohort:
        asset.cohort = new_cohort
    db.flush()
    chain.record(
        db,
        actor_id=actor_id,
        action="boundary.version_added",
        entity="asset",
        entity_id=asset.id,
        details={
            "version": version,
            "kind": kind,
            "status": status,
            "boundary_ids": created_ids,
            "source_name": source_name,
            "cohort_before": old_cohort,
            "cohort_after": new_cohort,
        },
        at=at,
    )
    db.expire_all()
    return list(db.execute(select(Boundary).where(Boundary.id.in_(created_ids)).order_by(Boundary.id)).scalars())


_SET_AT_SQL = text(
    """
    SELECT bv.id, bv.asset_id, bv.version, bv.kind::text AS kind, bv.status::text AS status,
           bv.source_name, bv.source_url, bv.source_date, bv.notification_ref, bv.certified_by,
           bv.valid_from, bv.valid_to, bv.effective_valid_to, bv.supersedes_id, bv.superseded_by_id,
           bv.derived_from_id, bv.sha256, ST_AsGeoJSON(bv.geom)::json AS geometry
    FROM boundary_versions bv
    WHERE bv.asset_id = :asset_id
      AND bv.version = (
          SELECT max(x.version) FROM boundary_versions x
          WHERE x.asset_id = :asset_id AND x.valid_from <= :on
            AND (x.effective_valid_to IS NULL OR x.effective_valid_to > :on))
    """
)


def boundary_set_at(db: Session, asset_id: int, on: dt.date) -> dict[str, dict]:
    """The boundary version in force on a date, keyed by kind. Empty if none was in force."""
    rows = db.execute(_SET_AT_SQL, {"asset_id": asset_id, "on": on}).mappings().all()
    return {r["kind"]: dict(r) for r in rows}


def current_boundary_set(db: Session, asset_id: int) -> dict[str, dict]:
    return boundary_set_at(db, asset_id, dt.date.today())


def primary_of(boundary_set: dict[str, dict]) -> dict | None:
    return boundary_set.get("ftl") or boundary_set.get("parcel")


def all_versions(db: Session, asset_id: int) -> list[dict]:
    rows = db.execute(
        text(
            """
            SELECT bv.id, bv.version, bv.kind::text AS kind, bv.status::text AS status, bv.source_name,
                   bv.source_url, bv.source_date, bv.notification_ref, bv.certified_by, bv.valid_from,
                   bv.valid_to, bv.effective_valid_to, bv.supersedes_id, bv.superseded_by_id,
                   bv.derived_from_id, bv.sha256, bv.created_at,
                   round((ST_Area(ST_Transform(bv.geom, 32644)))::numeric, 1) AS area_sq_m,
                   ST_AsGeoJSON(bv.geom)::json AS geometry
            FROM boundary_versions bv WHERE bv.asset_id = :a ORDER BY bv.version, bv.kind
            """
        ),
        {"a": asset_id},
    ).mappings()
    return [dict(r) for r in rows]
