"""The weekly digest: one official's area in one week (DECISIONS.md D-059).

Sent after each weekly screen. It counts the assets watched and seen clearly, names those with no
clear look, lists each change found that week with its incident, and says what is waiting for the
reader (D-067): reviews and recommendations for a district officer, approvals for a senior official.
The admin gets the State's figures with nothing waiting; field officers get none.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.enums import Role
from app.models import User
from app.notify import messages, routing
from app.services.alert_view import CHANGE_LABEL, WAITING_DAYS, describe

CLEAR = ("no_candidate", "candidate_found")


def week_dates(week: str) -> tuple[dt.date, dt.date]:
    year, num = week.split("-W")
    monday = dt.date.fromisocalendar(int(year), int(num), 1)
    return monday, monday + dt.timedelta(days=6)


def build(db: Session, user: User, week: str, at: dt.datetime) -> dict | None:
    """The digest's facts for this user, or None when the user covers no area."""
    areas = routing.areas_of(db, user.id)
    if user.role == Role.field_officer.value:
        return None
    admin = user.role in (Role.admin.value, Role.senior_official.value)
    if not admin and not areas:
        return None
    scope = routing.scope_sql(user)
    params = {"week": week}
    assets = db.execute(text(f"SELECT a.id, a.name, a.name_te FROM assets a WHERE a.monitored AND {scope} ORDER BY a.name"), params).mappings().all()
    ids = [a["id"] for a in assets] or [0]
    screens = {
        r["asset_id"]: r
        for r in db.execute(text(
            """
            SELECT DISTINCT ON (s.asset_id) s.asset_id, s.status, s.changes
            FROM asset_screens s JOIN screen_runs r ON r.id = s.run_id
            WHERE coalesce(s.week, to_char(r.as_of, 'IYYY-"W"IW')) = :week AND s.asset_id = ANY(:ids)
            ORDER BY s.asset_id, r.as_of DESC, s.id DESC
            """), {**params, "ids": ids}).mappings()
    }
    by_id = {a["id"]: a for a in assets}
    no_clear = [{"asset_id": a["id"], "asset_name": a["name"], "asset_name_te": a["name_te"]}
                for a in assets if (screens.get(a["id"]) or {}).get("status") not in CLEAR]
    entries = [(aid, c) for aid, s in screens.items() if s["status"] == "candidate_found" for c in (s["changes"] or [])]
    codes = dict(db.execute(text("SELECT id, code FROM alerts WHERE id = ANY(:ids)"),
                            {"ids": [c.get("alert_id") for _, c in entries if c.get("alert_id")] or [0]}).all())
    changes = [{
        "asset_id": aid, "asset_name": by_id[aid]["name"], "asset_name_te": by_id[aid]["name_te"],
        "change_type": c["change_type"], "change_label": CHANGE_LABEL.get(c["change_type"], c["change_type"]),
        "area_sq_m": c.get("area_sq_m"), "alert_id": c.get("alert_id"), "alert_code": codes.get(c.get("alert_id")),
        "continues": c.get("outcome") == "recorded_on_open_incident",
    } for aid, c in sorted(entries, key=lambda e: (by_id[e[0]]["name"], e[1].get("candidate_id") or 0))]

    start, end = week_dates(week)
    incidents = db.execute(text(
        f"""
        SELECT al.id, al.code, al.state::text AS state, al.resolution, al.created_at, a.name AS asset_name, a.name_te AS asset_name_te,
               c.change_type::text AS change_type, c.area_sq_m, c.first_changed_at,
               (SELECT l.zone::text FROM legal_checks l WHERE l.candidate_id = c.id ORDER BY l.id DESC LIMIT 1) AS zone,
               EXISTS (SELECT 1 FROM incident_reviews r WHERE r.alert_id = al.id AND r.reviewer_id = :uid) AS reviewed_by_me
        FROM alerts al JOIN candidates c ON c.id = al.candidate_id JOIN assets a ON a.id = c.asset_id
        WHERE {scope}
        """), {**params, "uid": user.id}).mappings().all()
    start_t = dt.datetime.combine(start, dt.time(), tzinfo=dt.timezone.utc)
    end_t = start_t + dt.timedelta(days=7)
    new = [i for i in incidents if start_t <= i["created_at"] < end_t and i["resolution"] != "auto"]
    reviewable = [i for i in incidents if i["state"] in ("OPEN", "UNDER_REVIEW", "FIELD_VISIT", "FIELD_REPORTED", "RECOMMENDED")]
    if user.role == Role.senior_official.value:
        waiting = [i for i in reviewable if i["state"] == "RECOMMENDED"]
    elif user.role == Role.admin.value:
        waiting = []
    else:
        waiting = [i for i in reviewable if i["state"] in ("OPEN", "UNDER_REVIEW", "FIELD_REPORTED") and not i["reviewed_by_me"]]
    waiting.sort(key=lambda i: i["created_at"])
    old = [i for i in reviewable if (at - i["created_at"]).days > WAITING_DAYS]

    def brief(i) -> dict:
        return {"alert_id": i["id"], "code": i["code"], "asset_name": i["asset_name"], "asset_name_te": i["asset_name_te"],
                "state": i["state"], "days_open": (at - i["created_at"]).days,
                "summary": describe(i["change_type"], float(i["area_sq_m"]) if i["area_sq_m"] else None, i["zone"], i["first_changed_at"])}

    return {
        "week": week,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "role": user.role,
        "scope": "all" if admin else "areas",
        "areas": [routing.area_label(a) for a in areas] if not admin else [],
        "figures": {
            "watched": len(assets),
            "clear_look": len(assets) - len(no_clear),
            "no_clear_look": len(no_clear),
            "changed": sum(1 for s in screens.values() if s["status"] == "candidate_found"),
            "new_incidents": len(new),
            "waiting_for_you": len(waiting),
            "open_over_14_days": len(old),
        },
        "no_clear_look": no_clear,
        "changes": changes,
        "new_incidents": [brief(i) for i in sorted(new, key=lambda i: i["created_at"])],
        "waiting": [brief(i) for i in waiting],
        "link": messages.link("/dashboard"),
    }
