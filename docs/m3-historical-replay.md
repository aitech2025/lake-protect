# M3 weekly historical replay

**Status:** implementation in progress on `feature/m3-historical-replay`.  
**Purpose:** replay the production Sentinel detector at historical weekly as-of dates without look-ahead. This is an engineering runner, not evidence that any case is true ground truth and not an accuracy result.

## Command

From the repository root:

```bash
cd pipeline
lp historical-replay \
  --start 2021-01-01 \
  --end 2025-12-31 \
  --assets ../data/assets.geojson \
  --out ../reports/m3/replay-v1 \
  --step-days 7
```

Use a fixed, versioned AOI/boundary snapshot for a replay. The dates above are illustrative only; select the actual period from independently verified case evidence and the detector's supported history window. The command reads the same rule configuration for every replay date.

## Outputs

- `replay-manifest.json`: date range, AOI/rules fingerprint, completed dates, status and unique detection count.
- `checkpoints/YYYY-MM-DD.json`: completed weekly result and detections for that as-of date.
- `weeks/YYYY-MM-DD/`: the ordinary per-week screen report, including candidate chips and coverage summary.
- `detections.geojson`: one feature per unique candidate event, with the first replay date it was emitted in `properties.detected_at`, the retrospective `first_changed_at`, and the replay as-of date.

The scorer must use `detected_at` as the time the system could first have raised the candidate. It must not substitute `first_changed_at`, which can predate the first replay run that had enough observations to satisfy persistence.

## Resume and reproducibility

The output directory is bound to:
- exact start/end dates and weekly step;
- the detector rule version and SHA-256;
- the asset keys, IDs, baseline dates and primary AOI geometries.

A mismatch is refused. Use a new output directory for a changed AOI snapshot, date range or rules file; never combine checkpoints from different configurations. Re-running the same command resumes completed weeks and retries missing/incomplete checkpoints. Existing STAC metadata and raster-window caches remain under `LP_CACHE_DIR`.

## Safety and interpretation

- STAC catalogue results are filtered to acquisitions on or before each replay date, and readers enforce the same as-of guard before reading pixels.
- `detected_at` is a replay timestamp, not a claim that an official received an alert on that historical date.
- Detection features remain review leads. Imagery indicates physical change, not ownership, title, encroachment or illegality.
- Do not score cases until event date, public-action date, event geometry, area and source provenance meet the case-register eligibility rules.
- Do not publish precision/recall or a 21/30 claim from unverified leads or an incomplete run.
