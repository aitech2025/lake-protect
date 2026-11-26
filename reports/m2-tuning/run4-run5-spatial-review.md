# M2 run4/run5 spatial comparison — human review required

**Generated:** 26 November 2026  
**Comparison workflow:** [run #45819230496](https://github.com/aitech2025/lake-protect/actions/runs/45819230496)  
**Output artifact:** [m2-run4-run5-spatial-diff (artifact 15117485673)](https://github.com/aitech2025/lake-protect/actions/runs/45819230496/artifacts/15117485673)  
**Run5 input:** [tuning run #45780430533](https://github.com/aitech2025/lake-protect/actions/runs/45780430533), artifact `m2-detect-v2-tuning-2026-11-20`  
**Comparison:** same asset + change type, one-to-one polygon IoU, threshold 0.10, projected to EPSG:32644.

## Result

| Measure | Run4 | Run5 / comparison |
|---|---:|---:|
| Candidate features | 14 | 3 |
| Spatially matched | — | 2 |
| Run4 footprints without a run5 match | — | 12 |
| Run5 footprints without a run4 match | — | 1 |
| Change types | 14 clearing | 3 clearing |

The two spatial matches are partial overlaps, not exact footprint equivalence:

| Asset | Run4 area (acres) | Run5 area (acres) | IoU |
|---|---:|---:|---:|
| `osm-way-158331211` | 12.0340 | 4.6209 | 0.34800 |
| `osm-way-265159686` | 1.7792 | 0.5683 | 0.31944 |

### Run4 unmatched footprints

- `osm-way-158331211`: 4 features — indices 0, 1, 2 and 4 in the run4 export.
- `osm-way-265159686`: 8 features — indices 6 through 13 in the run4 export.

Their per-feature area sum is 6.3752 acres. This is an export-level sum and must not be interpreted as unique land area because candidate geometries may overlap.

### Run5 unmatched footprint

- `osm-way-158331211`, first_changed_at `2026-11-08`, area 0.5931 acres.

## Interpretation and mandatory review

This is a spatial correspondence report only. The 12 unmatched run4 features are **not** automatically false positives; the unmatched run5 feature is **not** automatically a true positive. IoU can be affected by segmentation, polygon fragmentation, temporal thresholds, and candidate extraction. The two matched footprints also changed materially in area and require visual inspection.

Before detect-v2 can be frozen:
1. Inspect each of the 12 unmatched run4 footprints against the weekly imagery and before/after chips.
2. Inspect the one unmatched run5 footprint.
3. Inspect the two partial-overlap matches and explain the area/shape change.
4. Review the separate sub-threshold levelling diagnostic geometries/chips from PR #25.
5. Record a human disposition, reviewer, review date and evidence for every item.

No detector accuracy, false-positive, legal-status or enforcement conclusion is made by this report. Rule freeze and the M3 scored backtest remain blocked until this review and the independent case-evidence gate are complete.
