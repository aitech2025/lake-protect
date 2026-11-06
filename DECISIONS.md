# Decisions

Choices that change, or fill a gap in, `CONTEXT.md`. `CONTEXT.md` itself is not edited.

## Owner instructions that override CONTEXT.md

### D-001: Build order changed by the owner (5 Nov 2026)
`CONTEXT.md` section 12 orders M0 to M9 and stops after M3. The owner's instruction is: M0, M1,
then M4 to M9 on demo data with demo image pairs, then M2 and M3, with the stop moved from after
M3 to after M9, and the backtest reported at the end.

**Reading applied:** build M0, M1, M4 to M9, stop and report, then build M2 and M3 and report the
backtest as section 8.6 requires.

**Conflict inside the instruction:** its "when to stop" list still says not to start M4 until the
owner replies "Continue to M4". M4 now comes before M3, so that line cannot apply. The goal line
wins. The section 8.6 report and the "partial result, not a Gate 1 pass" wording still apply at M3.

**Consequence to keep in view:** section 1 puts the backtest first because it shows whether
detection works before anyone sees a pitch. Under this order the demo exists before there is any
detection result, so section 14's "open with its real result" cannot be used yet, and the demo
must not imply that detection has been shown to work.

## Errors and gaps found in CONTEXT.md

## Defaults changed
