#!/usr/bin/env python3
"""Summarize a five-lake M2 tuning report without making accuracy claims."""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

folder = Path(sys.argv[1])
lines = ["## M2 detect-v2 tuning run"]
summary_path = folder / "summary.json"
features_path = folder / "candidates.geojson"
if not summary_path.is_file() or not features_path.is_file():
    lines.append("The detector report is incomplete or was not generated. Inspect the failed workflow step.")
    rendered = "\n".join(lines) + "\n"
    print(rendered)
    summary_file = folder / "run5-summary.md"
    if folder.exists():
        summary_file.write_text(rendered, encoding="utf-8")
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with open(target, "a", encoding="utf-8") as stream:
            stream.write(rendered)
    raise SystemExit(0)

summary = json.loads(summary_path.read_text(encoding="utf-8"))
features = json.loads(features_path.read_text(encoding="utf-8")).get("features", [])
if summary.get("rule_version") != "detect-v2":
    raise SystemExit(f"Expected detect-v2 report, found {summary.get('rule_version')!r}")

by_type = Counter()
by_asset = Counter()
by_flag = Counter()
area_by_type = Counter()
for feature in features:
    p = feature.get("properties") or {}
    change = p.get("change_type") or "unknown"
    asset = p.get("asset_key") or p.get("asset_name") or "unknown"
    by_type[change] += 1
    by_asset[asset] += 1
    area_by_type[change] += float(p.get("area_sq_m") or 0)
    by_flag.update(p.get("flags") or [])

lines += [
    f"- As-of date: **{summary.get('as_of')}**",
    f"- Rule version: **{summary.get('rule_version')}**",
    f"- Rules SHA-256: `{summary.get('rules_sha256')}`",
    f"- Assets screened: **{len(summary.get('assets', []))}**",
    f"- Unique candidates in this screen: **{len(features)}**",
    "",
    "### Candidates by change type",
]
if by_type:
    for name, count in sorted(by_type.items()):
        lines.append(f"- {name}: {count} ({area_by_type[name] / 4046.86:.2f} acres total)")
else:
    lines.append("- None")
lines += ["", "### Candidates by tuning lake"]
for name, count in sorted(by_asset.items()):
    lines.append(f"- {name}: {count}")
if not by_asset:
    lines.append("- None")
lines += ["", "### Candidate flags"]
for name, count in sorted(by_flag.items()):
    lines.append(f"- {name}: {count}")
if not by_flag:
    lines.append("- None")
lines += ["", "### Transition pixels before and after controls"]
for name in ("soil_fill", "clearing", "building", "levelling"):
    raw = sum(int((asset.get("counts") or {}).get(f"px_{name}_raw", 0)) for asset in summary.get("assets", []))
    kept = sum(int((asset.get("counts") or {}).get(f"px_{name}_kept", 0)) for asset in summary.get("assets", []))
    lines.append(f"- {name}: {raw} raw transition pixels; {kept} pixels survive controls and baseline")
lines += ["", "### Radar details for building candidates"]
radar_rows = []
for feature in features:
    p = feature.get("properties") or {}
    if p.get("change_type") != "building":
        continue
    radar = p.get("radar") or {}
    radar_rows.append(
        f"- {p.get('asset_key')}: {radar.get('status', 'not_run')}; "
        f"looks before/after/season={radar.get('looks_before')}/{radar.get('looks_after')}/{radar.get('looks_season')}; "
        f"rise={radar.get('rise_db')} dB; seasonal rise={radar.get('rise_vs_last_year_db')} dB"
    )
lines.extend(radar_rows or ["- No building candidates"])
lines += [
    "",
    "### Interpretation",
    "This is a rule-tuning comparison on the five non-scored lakes only. Candidate counts and areas are not precision, recall, or accuracy. Review each candidate against the dated image chips and known restoration activity before changing a threshold.",
    "The previous detect-v1 run4 produced 14 candidates; differences must be inspected, with particular attention to the new levelling class.",
]
rendered = "\n".join(lines) + "\n"
(folder / "run5-summary.md").write_text(rendered, encoding="utf-8")
print(rendered)
target = os.environ.get("GITHUB_STEP_SUMMARY")
if target:
    with open(target, "a", encoding="utf-8") as stream:
        stream.write(rendered)
