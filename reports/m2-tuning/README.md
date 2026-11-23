# M2 tuning record: Sentinel-2 detection on five tuning lakes

**Real data, real lakes, not the scored backtest.** These five lakes are outside the section 13
case list (DECISIONS.md D-045). Thresholds may change only on evidence from them. Every run used
only scenes acquired on or before 20 November 2026, from Earth Search `sentinel-2-c1-l2a`, with
baseline 19 July 2024 (D-039). Each folder holds `summary.json` (coverage and what each control
removed, per lake) and `candidates.geojson`. Chips are rebuilt by rerunning; they are not committed.

Rerun any of them (cached imagery makes it take seconds):

```powershell
$env:LP_CACHE_DIR = "C:\lp-cache"
C:\lp-cache\venv\Scripts\lp detect --asset osm-way-27934981 --asset osm-way-265159686 --asset osm-way-158331211 `
  --asset osm-way-28847688 --asset osm-way-263825342 --as-of 2026-11-20 --out reports/m2-tuning/runN
```

## Runs

| Run | Rules | Change from the previous run | Candidates | Where |
|---|---|---|---|---|
| run1 | detect-v0 + novelty (D-042) | Section 8.4 starting values, plus novelty | 29 | Kapra 18, Gangaram 11 |
| run2 | as run1 + established 0.6 (D-050) | The old state must hold in 60% of the year's looks | 22 | Kapra 13, Gangaram 9 |
| run3 | established 0.85 | Tried, then reverted: see below | 19 | Kapra 10, Gangaram 9 |
| run4 | **detect-v1** | Established back to 0.6; patches within 30 m merged (D-051); radar check on built (D-049) | **14** | Kapra 9, Gangaram 5 |

Saroor Nagar Lake, Peeran Cheruvu and Gopi Cheruvu had no candidate in any run, from 71 to 77
clear looks each between December 2022 and November 2026.

## What the controls removed (run4, pixels across all five lakes)

| Stage | Pixels |
|---|---|
| Changed class at all | 12,631 |
| Water loss alone (never alerts, invariant 8) | 1,096 |
| Old state not stable before the change | 3,628 |
| Not persistent (two looks, 5 days, no reversal) | 2,269 |
| Newest look too old | 545 |
| Same season in earlier years showed the new state | 2,318 |
| New state already common in the year before (novelty) | 761 |
| Old state not established in the year before | 434 |
| Kept | 1,576 |

Then: 2 "building" candidates at Gangaram Cheruvu were dropped because radar did not confirm them
(VV rose 0.4 dB and 1.6 dB against a 3 dB rule), and 1 soil-fill candidate was dropped by the
drought control.

## What the candidates are

All 14 are at the two lakes where HYDRAA's own restoration works were reported in 2026:

- **Kapra Lake:** Phase II restoration began with a bhoomi puja in June 2026, with desilting, and was
  reported about 60% complete by October 2026 (Siasat, Deccan Chronicle, GK Today). The candidates'
  first changed dates run from June to November 2026.
- **Gangaram Cheruvu:** one of HYDRAA's 14 second-phase lakes; the Commissioner ordered its works
  sped up in February 2026 (Hyderabad Mail). The largest candidate, 4.9 ha of vegetated lake bed
  turned bare between 14 October and 8 November 2026, is inside the outline.

So the screen is seeing real earthworks, and it is silent at the three lakes with no reported
works. That is the case CONTEXT.md section 4 warns about: "lake restoration looks like
encroachment from space". These candidates are exactly what the authorised-works register exists
to close (legal check, `CLOSED_AUTHORISED`). No works record has been loaded: the public reports
give no work order reference or footprint, and the prototype does not invent one (rule 6).

**What this is not:** a measure of accuracy. Five lakes, no ground visits, and the press reports
only say works were under way, not where. Precision and lead time come from the blind backtest
(M3) and, later, field confirmation.

## Why run3 was reverted

Run3 tested the idea that the clearings were seasonal grass by requiring the old state in 85% of
the year's looks. The index history showed abrupt, persistent removal of dense vegetation (NDVI
0.86 to 0.20 in 25 days, bare since), and the press reports then explained it. The stricter value
was answering a wrong hypothesis, so detect-v1 keeps 0.6.

## Disclosure for the backtest

Before this tuning, Durgam Cheruvu, a scored case lake, was run once as the pipeline's first smoke
test, and the novelty control followed from what it showed (D-042). The M3 report must say so.
