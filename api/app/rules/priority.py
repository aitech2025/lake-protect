"""Priority score (CONTEXT.md section 6.4). Rule-based and owner-blind. Every factor is stored."""
from __future__ import annotations

import math

from app.rules import config as rules


def _clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def score(*, stage: str | None, area_sq_m: float, growth: float | None, cohort: str) -> tuple[float, dict]:
    cfg = rules.rules()["priority"]
    w = cfg["weights"]
    stage_f = cfg["stage"].get(stage, cfg["default_stage_factor"]) if stage else cfg["default_stage_factor"]
    area_f = _clip((math.log10(max(area_sq_m, 1.0)) - 3) / 2)
    growth_f = _clip(growth or 0.0)
    cohort_f = cfg["cohort"][cohort]
    total = 100 * (w["stage"] * stage_f + w["area"] * area_f + w["growth"] * growth_f + w["cohort"] * cohort_f)
    factors = {
        "rule_version": rules.rule_version(),
        "stage": {"input": stage, "factor": stage_f, "weight": w["stage"]},
        "area": {"input_sq_m": round(area_sq_m, 1), "factor": round(area_f, 4), "weight": w["area"]},
        "growth": {"input": growth, "factor": round(growth_f, 4), "weight": w["growth"]},
        "cohort": {"input": cohort, "factor": cohort_f, "weight": w["cohort"]},
        "computed_score": round(total, 2),
    }
    return round(total, 2), factors
