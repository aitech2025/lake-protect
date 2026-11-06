"""Monthly page figures (CONTEXT.md section 9.4). Everything comes from the database, never by hand.

A month's figures are worked out as at the end of that month (or now, for the current month) by
replaying the audit log, so last month's overdue list is what was overdue then, not what is now.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.clock import as_utc
from app.workflow.state_machine import SYSTEM_CLOSURES
from app.workflow.timers import TIMED_STATES

TIMED = {s.value for s in TIMED_STATES}
# Who answers for an overdue alert in each timed state (DECISIONS.md D-035).
RESPONSIBLE = {"TRIAGE": "Analyst desk", "FIELD_CONFIRMED": "Nodal officer (case file)", "WITH_OFFICER": "Officer"}


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


def _alerts(db: Session, demo: bool) -> list[dict]:
    rows = db.execute(text(
        """
        SELECT al.id, al.code, al.created_at, a.name AS asset_name, a.id AS asset_id,
               ST_X(ST_PointOnSurface(c.geom)) AS lon, ST_Y(ST_PointOnSurface(c.geom)) AS lat
        FROM alerts al JOIN candidates c ON c.id = al.candidate_id JOIN assets a ON a.id = c.asset_id
        WHERE al.is_demo = :demo
        """), {"demo": demo}).mappings().all()
    return [dict(r) for r in rows]


def _transitions(db: Session, ids: list[int], before: dt.datetime) -> dict[int, list[dict]]:
    if not ids:
        return {}
    rows = db.execute(text(
        """
        SELECT entity_id::bigint AS alert_id, details, at FROM audit_log
        WHERE entity = 'alert' AND action = 'alert.transition' AND at < :before AND entity_id = ANY(:ids)
        ORDER BY id
        """), {"before": before, "ids": [str(i) for i in ids]}).mappings().all()
    out: dict[int, list[dict]] = {}
    for r in rows:
        out.setdefault(r["alert_id"], []).append({**r["details"], "at": r["at"]})
    return out


def compute(db: Session, month: str, *, demo: bool, now: dt.datetime | None = None) -> dict:
    w = window(month, now)
    alerts = _alerts(db, demo)
    by_id = {a["id"]: a for a in alerts}
    history = _transitions(db, list(by_id), w.cutoff)
    users = {r.id: r.name for r in db.execute(text("SELECT id, name FROM users"))}

    def in_month(t: dt.datetime) -> bool:
        return w.start <= t < w.cutoff

    new_alerts, verified, actions, overdue = [], set(), set(), []
    for aid, steps in history.items():
        a = by_id[aid]
        if in_month(a["created_at"]) and steps and steps[0]["to"] not in SYSTEM_CLOSURES:
            new_alerts.append(aid)
        for s in steps:
            if s["to"] == "FIELD_CONFIRMED" and s["from"] == "ASSIGNED" and in_month(s["at"]):
                verified.add(aid)
            if s["to"] == "ACTION_RECORDED" and in_month(s["at"]):
                actions.add(aid)
        last = steps[-1]
        due = dt.datetime.fromisoformat(last["due_at"]) if last.get("due_at") else None
        if last["to"] in TIMED and due is not None and due < w.cutoff:
            owner_id = next((s["owner_user_id"] for s in reversed(steps) if s.get("owner_user_id")), None)
            who = users.get(owner_id, "Field officer") if last["to"] == "ASSIGNED" else RESPONSIBLE[last["to"]]
            overdue.append({
                "alert_id": aid, "code": a["code"], "asset_name": a["asset_name"], "state": last["to"], "due_at": due.isoformat(),
                "days_overdue": (w.cutoff - due).days, "responsible": who, "lon": a["lon"], "lat": a["lat"],
            })
    overdue.sort(key=lambda o: (-o["days_overdue"], o["code"]))
    watched = db.scalar(text(
        "SELECT count(DISTINCT a.id) FROM assets a JOIN boundaries b ON b.asset_id = a.id WHERE a.is_demo = :demo AND b.valid_from < :cut"),
        {"demo": demo, "cut": w.cutoff.date() + dt.timedelta(days=1)})
    by_responsible: dict[str, int] = {}
    for o in overdue:
        by_responsible[o["responsible"]] = by_responsible.get(o["responsible"], 0) + 1
    return {
        "month": month,
        "as_of": w.cutoff.isoformat(),
        "complete_month": w.cutoff == w.end,
        "dataset": "demo" if demo else "real",
        "counts": {"watched": watched, "new_alerts": len(new_alerts), "verified": len(verified), "action_taken": len(actions), "overdue": len(overdue)},
        "overdue": overdue,
        "overdue_by_responsible": [{"responsible": k, "count": v} for k, v in sorted(by_responsible.items(), key=lambda kv: -kv[1])],
        "new_alert_points": [{"code": by_id[i]["code"], "lon": by_id[i]["lon"], "lat": by_id[i]["lat"]} for i in new_alerts],
    }


def bulletin(db: Session, month: str, *, demo: bool, now: dt.datetime | None = None) -> dict:
    this = compute(db, month, demo=demo, now=now)
    last = compute(db, previous_month(month), demo=demo, now=now)
    this["last_month"] = {"month": last["month"], "counts": last["counts"]}
    return this
