"""The drill-down dashboard (DECISIONS.md D-060; CONTEXT.md section 17.7).

    State  >  district  >  mandal  >  village  >  lake or parcel  >  incident

At every level the same figures: assets watched, seen clearly this week, without a clear look,
changed this week, new incidents, open (awaiting review and under review), waiting more than 14
days, confirmed, and how many officials' notifications were acknowledged within 24 hours. Each
figure is counted with the incident list's own rules (app.services.alert_view), so every number
opens exactly the incidents behind it.

A level whose assets all lack the next area (the real lakes have no village) is skipped, and the
lakes are listed directly. Only locations being watched count as watched and in the weekly figures;
a location whose watch was stopped still shows while it has incidents (D-061). Assets with no district are grouped as "area not recorded". Real and
demo assets are never mixed. Everyone sees every area: areas decide who is notified, not who may
look.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import text
from sqlalchemy.orm import Session

from app import categories
from app.models import User
from app.notify import routing
from app.services import alert_view
from app.services.alert_view import NOT_RECORDED, in_area, is_waiting
from app.services.weeks import STATUS_LABEL

LEVELS = ("state", "district", "mandal", "village")
CLEAR = ("no_candidate", "candidate_found")
TREND_WEEKS = 8
ACK_WINDOW = dt.timedelta(days=30)
ACK_WITHIN = dt.timedelta(hours=24)
CONFIRMED_STATUSES = ("physically_marked", "final_notification", "surveyed_agency")

_ASSETS = text(
    """
    SELECT a.id, a.name, a.name_te, a.cohort::text AS cohort, a.type::text AS type, a.district, a.mandal, a.village,
           a.monitored, ST_X(b.p) AS lon, ST_Y(b.p) AS lat, b.status AS boundary_status
    FROM assets a
    LEFT JOIN LATERAL (
        SELECT ST_PointOnSurface(geom) AS p, status::text AS status FROM boundaries
        WHERE asset_id = a.id AND kind IN ('ftl', 'parcel') ORDER BY valid_from DESC, version DESC LIMIT 1) b ON true
    WHERE a.is_demo = :demo
    ORDER BY a.name
    """
)
_WEEKS = text(
    """
    SELECT DISTINCT coalesce(s.week, to_char(r.as_of, 'IYYY-"W"IW')) AS week
    FROM asset_screens s JOIN screen_runs r ON r.id = s.run_id WHERE r.is_demo = :demo
    ORDER BY week DESC LIMIT :n
    """
)
_SCREENS = text(
    """
    SELECT DISTINCT ON (s.asset_id, coalesce(s.week, to_char(r.as_of, 'IYYY-"W"IW')))
           s.asset_id, coalesce(s.week, to_char(r.as_of, 'IYYY-"W"IW')) AS week, s.status, jsonb_array_length(s.changes) AS changes
    FROM asset_screens s JOIN screen_runs r ON r.id = s.run_id
    WHERE r.is_demo = :demo AND coalesce(s.week, to_char(r.as_of, 'IYYY-"W"IW')) = ANY(:weeks)
    ORDER BY s.asset_id, coalesce(s.week, to_char(r.as_of, 'IYYY-"W"IW')), r.as_of DESC, s.id DESC
    """
)
_ACKS = text(
    """
    SELECT n.alert_id, n.created_at, n.acknowledged_at
    FROM notifications n JOIN users u ON u.id = n.user_id
    WHERE n.kind = 'incident_opened' AND u.role = 'viewer' AND n.is_demo = :demo AND n.created_at >= :since
    """
)


def _week_start(week: str) -> dt.datetime:
    year, num = week.split("-W")
    return dt.datetime.combine(dt.date.fromisocalendar(int(year), int(num), 1), dt.time(), tzinfo=dt.timezone.utc)


def _key(value: str | None) -> str:
    return (value or "").strip()


def _figures(assets: list[dict], incidents: list[dict], screens: dict, week: str | None, acks: list[dict], now: dt.datetime) -> dict:
    ids = {a["id"] for a in assets}
    watched = [a for a in assets if a.get("monitored", True)]
    mine = [i for i in incidents if i["asset_id"] in ids]
    this_week = {aid: s for (aid, w), s in screens.items() if w == week and aid in {a["id"] for a in watched}}
    start = _week_start(week) if week else None
    new = [i for i in mine if start and start <= i["created_at"] < start + dt.timedelta(days=7) and i["resolution"] != "auto"]
    alert_ids = {i["id"] for i in mine}
    considered = [n for n in acks if n["alert_id"] in alert_ids and (n["acknowledged_at"] or n["created_at"] <= now - ACK_WITHIN)]
    on_time = [n for n in considered if n["acknowledged_at"] and n["acknowledged_at"] - n["created_at"] <= ACK_WITHIN]
    clear = sum(1 for s in this_week.values() if s["status"] in CLEAR)
    return {
        "assets": len(watched),
        "clear_look": clear,
        "no_clear_look": len(watched) - clear,
        "changed": sum(1 for s in this_week.values() if s["status"] == "candidate_found"),
        "new_incidents": len(new),
        "open": sum(1 for i in mine if i["state"] == "OPEN"),
        "under_review": sum(1 for i in mine if i["state"] == "UNDER_REVIEW"),
        "waiting": sum(1 for i in mine if is_waiting(i, now)),
        "confirmed": sum(1 for i in mine if i["state"] == "CONFIRMED"),
        "court_matters": sum(1 for i in mine if i["state"] in ("OPEN", "UNDER_REVIEW") and i["court_matter"]),
        "boundary_confirmed": sum(1 for a in watched if a["boundary_status"] in CONFIRMED_STATUSES),
        "ack_considered": len(considered),
        "ack_on_time": len(on_time),
    }


def _tone(f: dict) -> str:
    """One word for a row's colour on the map and in the table."""
    if f["waiting"]:
        return "waiting"
    if f["open"] or f["under_review"]:
        return "open"
    if f["changed"]:
        return "changed"
    if f["assets"] and f["no_clear_look"] == f["assets"]:
        return "no_look"
    return "quiet"


def overview(db: Session, user: User, *, is_demo: bool, district: str | None = None, mandal: str | None = None,
             village: str | None = None, now: dt.datetime | None = None) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    path = {"district": district, "mandal": mandal, "village": village}
    depth = 0 if district is None else 1 if mandal is None else 2 if village is None else 3
    level = LEVELS[depth]

    every = [dict(r) for r in db.execute(_ASSETS, {"demo": is_demo}).mappings()]
    incidents = [i for i in alert_view.list_alerts(db) if i["is_demo"] == is_demo]
    with_incidents = {i["asset_id"] for i in incidents}
    assets = [a for a in every if in_area(a, district, mandal, village) and (a["monitored"] or a["id"] in with_incidents)]
    weeks = sorted(db.scalars(_WEEKS, {"demo": is_demo, "n": TREND_WEEKS}).all())
    week = weeks[-1] if weeks else None
    screens = {(r["asset_id"], r["week"]): dict(r) for r in db.execute(_SCREENS, {"demo": is_demo, "weeks": weeks or [""]}).mappings()}
    acks = [dict(r) for r in db.execute(_ACKS, {"demo": is_demo, "since": now - ACK_WINDOW}).mappings()]

    # The next level down; skipped while every asset here lacks it (real lakes have no village).
    child_level = None
    for nxt in LEVELS[depth + 1:]:
        if any(_key(a[nxt]) for a in assets):
            child_level = nxt
            break
    children = []
    if child_level:
        groups: dict[str, list[dict]] = {}
        for a in assets:
            groups.setdefault(_key(a[child_level]) or NOT_RECORDED, []).append(a)
        for name, members in sorted(groups.items(), key=lambda kv: (kv[0] == NOT_RECORDED, kv[0].lower())):
            f = _figures(members, incidents, screens, week, acks, now)
            pts = [(m["lon"], m["lat"]) for m in members if m["lon"] is not None]
            params = {**{k: v for k, v in path.items() if v is not None}, child_level: name}
            children.append({
                "kind": "area", "level": child_level, "name": name, "not_recorded": name == NOT_RECORDED, "params": params,
                "figures": f, "tone": _tone(f),
                "lon": sum(p[0] for p in pts) / len(pts) if pts else None, "lat": sum(p[1] for p in pts) / len(pts) if pts else None,
            })
    else:
        for a in assets:
            f = _figures([a], incidents, screens, week, acks, now)
            s = screens.get((a["id"], week)) if week else None
            children.append({
                "kind": "asset", "level": "asset", "asset_id": a["id"], "name": a["name"], "name_te": a["name_te"],
                "cohort": a["cohort"], "type": a["type"], "category": categories.category_of(a["type"]),
                "monitored": a["monitored"], "boundary_status": a["boundary_status"],
                "week_status": s["status"] if s else None, "week_status_label": STATUS_LABEL.get(s["status"], s["status"]) if s else "No record this week",
                "params": {k: v for k, v in path.items() if v is not None}, "figures": f, "tone": _tone(f), "lon": a["lon"], "lat": a["lat"],
            })

    ids = {a["id"] for a in assets}
    n_watched = sum(1 for a in assets if a["monitored"])
    trend = []
    for w in weeks:
        start = _week_start(w)
        rows = [s for (aid, ww), s in screens.items() if ww == w and aid in ids]
        trend.append({
            "week": w,
            "changed": sum(1 for s in rows if s["status"] == "candidate_found"),
            "clear_look": sum(1 for s in rows if s["status"] in CLEAR),
            "no_clear_look": n_watched - sum(1 for s in rows if s["status"] in CLEAR and s["asset_id"] in ids),
            "new_incidents": sum(1 for i in incidents if i["asset_id"] in ids and start <= i["created_at"] < start + dt.timedelta(days=7)
                                 and i["resolution"] != "auto"),
        })

    pins = []
    for a in assets:
        f = _figures([a], incidents, screens, week, acks, now)
        if a["lon"] is not None:
            pins.append({"asset_id": a["id"], "name": a["name"], "name_te": a["name_te"], "lon": a["lon"], "lat": a["lat"], "tone": _tone(f),
                         "monitored": a["monitored"]})

    by_type: dict[str, int] = {}
    for a in assets:
        if a["monitored"]:
            by_type[a["type"]] = by_type.get(a["type"], 0) + 1
    by_category = [{k: c[k] for k in ("name", "status", "label", "watched")} for c in categories.as_list(by_type) if c["status"] != "intake"]

    crumbs = [{"level": "state", "name": "Demo State" if is_demo else "Telangana", "params": {}}]
    for i, lvl in enumerate(LEVELS[1:depth + 1], start=1):
        crumbs.append({"level": lvl, "name": path[lvl], "params": {k: path[k] for k in LEVELS[1:i + 1]}})

    return {
        "dataset": "demo" if is_demo else "real",
        "level": level,
        "child_level": child_level or "asset",
        "path": crumbs,
        "filters": {k: v for k, v in path.items() if v is not None},
        "week": week,
        "figures": _figures(assets, incidents, screens, week, acks, now),
        "by_category": by_category,
        "children": children,
        "trend": trend,
        "pins": pins,
        "my_areas": routing.areas_of(db, user.id),
        "area_source": None if is_demo else "Districts and mandals of the OpenStreetMap lakes come from OpenStreetMap boundaries, not the revenue record.",
        "as_of": now.isoformat(),
    }


def known_areas(db: Session) -> list[dict]:
    """Every district and mandal that holds an asset, for the admin's area picker."""
    rows = db.execute(text(
        """
        SELECT btrim(district) AS district, btrim(mandal) AS mandal, is_demo, count(*) AS assets FROM assets
        WHERE coalesce(btrim(district), '') <> '' GROUP BY 1, 2, 3 ORDER BY 3, 1, 2
        """)).mappings().all()
    out: dict[tuple, dict] = {}
    for r in rows:
        d = out.setdefault((r["district"], r["is_demo"]), {"district": r["district"], "dataset": "demo" if r["is_demo"] else "real", "assets": 0, "mandals": []})
        d["assets"] += r["assets"]
        if r["mandal"]:
            d["mandals"].append({"mandal": r["mandal"], "assets": r["assets"]})
    return list(out.values())
