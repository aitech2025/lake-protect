# detect-v2 rule review and tuning gate

**Review date:** 26 November 2026  
**Status:** reviewed; freeze deliberately blocked pending detect-v2 tuning evidence.

## Findings

The active rule file is `pipeline/lake_protect/detect_rules.yaml`, version `detect-v2`.

The available five-lake tuning report, `reports/m2-tuning/README.md`, documents run4 on **detect-v1**:
- 14 candidates remained across Kapra Lake and Gangaram Cheruvu.
- Radar removed two building candidates that did not meet the 3 dB rise threshold.
- Drought control removed one soil-fill candidate.
- Saroor Nagar Lake, Peeran Cheruvu and Gopi Cheruvu had no candidate in that report.
- The report explicitly says this is not an accuracy result and discloses Durgam Cheruvu's pre-tuning exposure.

D-058 added `other>bare: levelling` to detect-v2 after run4. The decision says it was **not tuned** and may raise false changes on dry scrub. Therefore:
- Do not freeze or tag detect-v2 yet.
- Do not tune using the scored M3 case set.
- Run the five separate tuning lakes at the same historical cutoff as run4, inspect before/after chips and candidate flags, then decide whether any rule change is justified.
- If thresholds change, increment the rule version and disclose the change. Never modify thresholds in response to scored-case results.

## Reproducible run

The workflow `.github/workflows/m2-tuning.yml` runs on pushes to `feature/m2-tuning-detect-v2` and can also be started manually from GitHub Actions. It:
1. verifies the active rule version is detect-v2;
2. screens the same five non-scored lake AOIs as run4 at 20 November 2026;
3. saves the normal screen report and before/after candidate chips;
4. writes a candidate summary by change type, lake and flag; and
5. uploads the report as a workflow artifact.

The five tuning AOI keys are `osm-way-27934981`, `osm-way-265159686`, `osm-way-158331211`, `osm-way-28847688` and `osm-way-263825342`.

## Freeze decision

M3.6 review is complete, but its outcome is **not ready to freeze**. M3.7 remains blocked until run5 is inspected and the owner-approved detect-v2 rule set is stable. The scored replay must use an immutable tag containing the exact rule file and dependency versions. No scored replay or accuracy claim is authorized by this review.
