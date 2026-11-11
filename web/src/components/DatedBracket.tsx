import type { CSSProperties } from "react";
import { useTranslation } from "react-i18next";
import { fmtDate } from "../api";

type Props = { baseline: string; cutoff: string; lastClear: string | null; firstChanged: string; detected: string };
type Anchor = "start" | "mid" | "end";

/**
 * The dated bracket (section 8.4) drawn as a time strip, with the policy cut-off and baseline.
 * Labels never leave the strip (UI audit A10): the change window is one line above the axis,
 * aligned towards where the change sits, and the dated marks below are anchored to the nearer
 * edge when they are close to one.
 */
export function DatedBracket({ baseline, cutoff, lastClear, firstChanged, detected }: Props) {
  const { t, i18n } = useTranslation();
  const day = (s: string) => new Date(s.slice(0, 10) + "T00:00:00Z").getTime();
  const points = [baseline, cutoff, lastClear ?? firstChanged, firstChanged, detected].map(day);
  const start = Math.min(...points);
  const end = Math.max(...points);
  const pad = (end - start) * 0.06 || 86_400_000;
  const pos = (s: string) => ((day(s) - (start - pad)) / (end - start + 2 * pad)) * 100;
  const lang = i18n.language;

  const anchorOf = (p: number): Anchor => (p < 15 ? "start" : p > 85 ? "end" : "mid");
  // An end-anchored mark is placed from the right, so it can use the room to its left.
  const place = (p: number): CSSProperties => (anchorOf(p) === "end" ? { right: `${100 - p}%` } : { left: `${p}%` });
  const windowAt = lastClear ? (pos(lastClear) + pos(firstChanged)) / 2 : pos(firstChanged);
  const windowAlign: Anchor = windowAt < 33 ? "start" : windowAt > 66 ? "end" : "mid";

  // Dated marks in time order. A mark too close to the one before it on the same row drops to a
  // second row, so labels never overlap; on a narrow strip the CSS lists them under the axis instead.
  const marks = [
    { at: cutoff, label: t("detail.cutoff") },
    { at: baseline, label: t("detail.baseline") },
    { at: detected, label: t("detail.detected") },
  ]
    .map((m) => ({ ...m, p: pos(m.at) }))
    .sort((x, y) => x.p - y.p);
  const lastOnRow = [-Infinity, -Infinity];
  const placed = marks.map((m) => {
    const row = m.p - lastOnRow[0] >= 24 ? 0 : 1;
    lastOnRow[row] = m.p;
    return { ...m, row };
  });
  const twoRows = placed.some((m) => m.row === 1);
  return (
    <div>
      <div className="bracket-wrap" data-testid="dated-bracket">
        <p className={`bracket-window at-${windowAlign}`}>
          {lastClear && (
            <span>
              {t("detail.last_clear")} <b>{fmtDate(lastClear, lang)}</b>
            </span>
          )}
          <span>
            {t("detail.first_changed")} <b>{fmtDate(firstChanged, lang)}</b>
          </span>
        </p>
        <div className={`bracket${twoRows ? " two-rows" : ""}`}>
          <div className="axis" />
          {lastClear && <div className="span" style={{ left: `${pos(lastClear)}%`, width: `${Math.max(0.6, pos(firstChanged) - pos(lastClear))}%` }} />}
          {placed.map((m) => (
            <div key={m.label} className="mark-group">
              <div className="tick" style={{ left: `${m.p}%` }} />
              <div className={`mark at-${anchorOf(m.p)} row-${m.row}`} style={place(m.p)}>
                {m.label}
                <b>{fmtDate(m.at, lang)}</b>
              </div>
            </div>
          ))}
        </div>
      </div>
      <p className="small muted bracket-note">{t("detail.bracket_note")}</p>
    </div>
  );
}
