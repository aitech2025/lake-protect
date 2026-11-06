"""Loads rules/config.yaml once. Rules read configuration from here, never from constants."""
from __future__ import annotations

import datetime as dt
from functools import lru_cache
from pathlib import Path

import yaml

from app.enums import BoundaryStatus, Cohort, Mode

CONFIG_PATH = Path(__file__).with_name("config.yaml")


@lru_cache(maxsize=1)
def rules() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def rule_version() -> str:
    return rules()["rule_version"]


def mode_for_cohort(cohort: str) -> Mode:
    return Mode(rules()["mode_by_cohort"][Cohort(cohort).value])


def cohort_for_status(status: str) -> Cohort:
    return Cohort(rules()["cohort_by_boundary_status"][BoundaryStatus(status).value])


def is_confirmed_status(status: str) -> bool:
    return BoundaryStatus(status).value in rules()["confirmed_boundary_statuses"]


def lake_buffer_width_m(area_ha: float) -> float:
    cfg = rules()
    widths = cfg["buffer_widths_m"]
    return widths["lake_10ha_or_more"] if area_ha >= cfg["lake_size_threshold_ha"] else widths["lake_under_10ha"]


def watch_ring_m() -> float:
    return rules()["watch_ring_m"]


def policy_cutoff_date() -> dt.date:
    return dt.date.fromisoformat(str(rules()["policy_cutoff_date"]))


def live_court_statuses() -> list[str]:
    return rules()["live_court_statuses"]
