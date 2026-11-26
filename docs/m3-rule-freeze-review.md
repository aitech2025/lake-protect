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


## detect-v2 run5 result — 26 November 2026

Workflow run [#8](https://github.com/aitech2025/lake-protect/actions/runs/45780430533) completed on the same five non-scored tuning lakes and the same 20 November 2026 as-of cutoff. Artifact: `m2-detect-v2-tuning-2026-11-20` (artifact ID `15098336015`, expires 26 December 2026).

- Rules SHA-256: `7e3ae2398bab87c1133a7a6ecefafe5b4407c8a7a428fdc0b7999cb998fa2a36`.
- Five lakes screened; **3 final candidates**, all classified as clearing, totalling **5.78 acres**: two at Gangaram Cheruvu and one at Kapra Lake.
- No building candidate remained in this corrected run.
- The new levelling transition was exercised: **2,068 raw OTHER→BARE pixels**, of which **72 survived the temporal controls and baseline check**. No final levelling candidate met the candidate extraction gates.
- Per-lake levelling counts: Gangaram Cheruvu 989 raw / 31 kept; Gopi Cheruvu 69 / 7; Kapra Lake 880 / 31; Saroor Nagar Lake 76 / 2; Peeran Cheruvu 54 / 1.
- Detect-v1 run4 had 14 clearing candidates (20.19 acres). Detect-v2 run5 now has 3 clearing candidates (5.78 acres). This is a material change and must not be interpreted as improved accuracy without inspecting the areas that disappeared.
- The first detect-v2 attempt was invalid: `OTHER` was excluded from the informative time series, making D-058's OTHER→BARE transition unreachable. The code now treats only `MASKED` as uninformative and has a synthetic regression test for levelling. The run above uses the corrected implementation.
- The run's candidate chips cover only the three emitted candidates; the 72 levelling pixels that survived controls do not yet have diagnostic component chips. The previous 11 run4 candidate areas that no longer appear also need a targeted before/after review.

**Decision:** do not freeze detect-v2 yet. D-058 is now active and exercised, but the changed candidate set needs diagnostic chips and human review. No threshold was tuned from scored cases, and no accuracy metric is inferred from this run.

## Remaining review actions

1. Export geometry and before/after chips for levelling components that survive temporal controls but fail the final area/component gates.
2. Compare the 11 run4 candidate footprints no longer emitted by run5; decide whether they are correctly reclassified as small levelling patches or whether the new informative-state behavior suppresses real clearing.
3. Only after that review, finalize the rule set and create the immutable pre-score tag required by M3.7.
