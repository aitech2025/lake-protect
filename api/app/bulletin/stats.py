"""Monthly page figures (CONTEXT.md section 9.4, incidents since D-057). Everything comes from the
database, never by hand.

A month's figures are worked out as at the end of that month (or now, for the current month) by
replaying the audit log, so last month's waiting list is what was waiting then, not what is now.

The five figures: assets watched, new incidents, incidents reviewed by officials, changes
confirmed, and incidents waiting more than WAIT_DAYS for a decision.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.clock import as_utc

WAIT_DAYS = 14
WAITING_STATES = ("OPEN", "UNDER_REVIEW")


@dataclass(frozen=True)
class Window:
    month: str
    start: dt.datetime
    end: dt.datetime  # exclusive
    cutoff: dt.datetime  # end of month, or now for the current month


def window(month: str, now: dt.datetime | None = None) -> Window:
    year, mon = (int(p) for p in month.split("-"))
    start = dt.datetime(year, mon, 1, tzinfo=dt.timezone.utc)
    end = dt.datetime(year + (mon == 12), mon % 12 + 1, 1, tzinfo=dt.timezone.utc)
    return Window(month, start, end, min(end, as_utc(now)))


def previous_month(month: str) -> str:
    year, mon = (int(p) for p in month.split("-"))
    return f"{year - (mon == 1)}-{(mon - 2) % 12 + 1:02d}"


def _incidents(db: Session, demo: bool) -> list[dict]:
    rows = db.execute(text(
        """
        SELECT al.id, al.code, al.created_at, al.resolution, a.name AS asset_name, a.id AS asset_id,
               c.change_type::text AS change_type,
               ST_X(ST_PointOnSurface(c.geom)) AS lon, ST_Y(ST_PointOnSurface(c.geom)) AS lat
        FROM alerts al JOIN candidates c ON c.id = al.candidate_id JOIN assets a ON a.id = c.asset_id
        WHERE al.is_demo = :demo
        """), {"demo": demo}).mappings().all()
    return [dict(r) for r in rows]


def _events(db: Session, ids: list[int], before: dt.datetime) -> dict[int, list[dict]]:
    if not ids:
        return {}
    rows = db.execute(text(
        """
        SELECT entity_id::bigint AS alert_id, action, details, at FROM audit_log
        WHERE entity = 'alert' AND action IN ('alert.transition', 'incident.reviewed') AND at < :before
          AND entity_id = ANY(:ids)
        ORDER BY id
        """), {"before": before, "ids": [str(i) for i in ids]}).mappings().all()
    out: dict[int, list[dict]] = {}
    for r in rows:
        out.setdefault(r["alert_id"], []).append({**r["details"], "action": r["action"], "at": r["at"]})
    return out


def compute(db: Session, month: str, *, demo: bool, now: dt.datetime | None = None) -> dict:
    w = window(month, now)
    incidents = [i for i in _incidents(db, demo) if i["created_at"] < w.cutoff]
    by_id = {i["id"]: i for i in incidents}
    events = _events(db, list(by_id), w.cutoff)

    def in_month(t: dt.datetime) -> bool:
        return w.start <= t < w.cutoff

    new, reviewed, confirmed, waiting = [], set(), set(), []
    change_types: dict[str, int] = {}
    for iid, inc in by_id.items():
        steps = events.get(iid, [])
        transitions = [s for s in steps if s["action"] == "alert.transition"]
        auto = any(t.get("resolution") == "auto" for t in transitions)
        if in_month(inc["created_at"]) and not auto:
            new.append(iid)
            change_types[inc["change_type"]] = change_types.get(inc["change_type"], 0) + 1
        for s in steps:
            if s["action"] == "incident.reviewed" and in_month(s["at"]):
                reviewed.add(iid)
            if s["action"] == "alert.transition" and s.get("to") == "CONFIRMED" and in_month(s["at"]):
                confirmed.add(iid)
        state = transitions[-1]["to"] if transitions else "OPEN"
        days = (w.cutoff - inc["created_at"]).days
        if state in WAITING_STATES and not auto and days > WAIT_DAYS:
            waiting.append({
                "alert_id": iid, "code": inc["code"], "asset_name": inc["asset_name"], "state": state,
                "created_at": inc["created_at"].isoformat(), "days_waiting": days, "lon": inc["lon"], "lat": inc["lat"],
            })
    waiting.sort(key=lambda o: (-o["days_waiting"], o["code"]))
    watched = db.scalar(text(
        "SELECT count(DISTINCT a.id) FROM assets a JOIN boundaries b ON b.asset_id = a.id WHERE a.is_demo = :demo AND b.valid_from < :cut"
        # Watched at the cut-off: the last start or stop before it (D-061); no row means watched.
        " AND coalesce((SELECT m.monitored FROM monitoring_changes m WHERE m.asset_id = a.id AND m.at < :cut"
        " ORDER BY m.at DESC, m.id DESC LIMIT 1), true)"),
        {"demo": demo, "cut": w.cutoff.date() + dt.timedelta(days=1)})
    by_state: dict[str, int] = {}
    for o in waiting:
        by_state[o["state"]] = by_state.get(o["state"], 0) + 1
    return {
        "month": month,
        "as_of": w.cutoff.isoformat(),
        "complete_month": w.cutoff == w.end,
        "dataset": "demo" if demo else "real",
        "wait_days": WAIT_DAYS,
        "counts": {"watched": watched, "new_alerts": len(new), "reviewed": len(reviewed), "confirmed": len(confirmed), "waiting": len(waiting)},
        "change_types": change_types,
        "waiting": waiting,
        "waiting_by_state": [{"state": k, "count": v} for k, v in sorted(by_state.items(), key=lambda kv: -kv[1])],
        "new_alert_points": [{"code": by_id[i]["code"], "lon": by_id[i]["lon"], "lat": by_id[i]["lat"]} for i in new],
    }


def bulletin(db: Session, month: str, *, demo: bool, now: dt.datetime | None = None) -> dict:
    this = compute(db, month, demo=demo, now=now)
    last = compute(db, previous_month(month), demo=demo, now=now)
    this["last_month"] = {"month": last["month"], "counts": last["counts"]}
    return this
