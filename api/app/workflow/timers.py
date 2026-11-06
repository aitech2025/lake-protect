"""Timers (CONTEXT.md section 6.6). Proposed defaults from rules/config.yaml."""
from __future__ import annotations

import datetime as dt

from app.enums import AlertState
from app.rules import config as rules

TIMED_STATES = {AlertState.TRIAGE, AlertState.ASSIGNED, AlertState.FIELD_CONFIRMED, AlertState.WITH_OFFICER}

# Who hears about a missed timer.
ON_MISS = {
    AlertState.TRIAGE: "reviewer",
    AlertState.ASSIGNED: "nodal_officer",
    AlertState.FIELD_CONFIRMED: "legal_officer",
    AlertState.WITH_OFFICER: "monthly_overdue_list",
}


def is_monsoon(day: dt.date) -> bool:
    return day.month in rules.rules()["monsoon_months"]


def due_for(state: str, entered_at: dt.datetime) -> dt.datetime | None:
    s = AlertState(state)
    if s not in TIMED_STATES:
        return None
    days = rules.rules()["timers_days"]
    n = days["ASSIGNED_MONSOON"] if s == AlertState.ASSIGNED and is_monsoon(entered_at.date()) else days[s.value]
    return entered_at + dt.timedelta(days=n)


def is_overdue(state: str, due_at: dt.datetime | None, now: dt.datetime) -> bool:
    return due_at is not None and AlertState(state) in TIMED_STATES and now > due_at
