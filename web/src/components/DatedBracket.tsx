import { useTranslation } from "react-i18next";
import { fmtDate } from "../api";

type Props = { baseline: string; cutoff: string; lastClear: string | null; firstChanged: string; detected: string };

/** The dated bracket (section 8.4) drawn as a time strip, with the policy cut-off and baseline. */
export function DatedBracket({ baseline, cutoff, lastClear, firstChanged, detected }: Props) {
  const { t, i18n } = useTranslation();
  const day = (s: string) => new Date(s.slice(0, 10) + "T00:00:00Z").getTime();
  const points = [baseline, cutoff, lastClear ?? firstChanged, firstChanged, detected].map(day);
  const start = Math.min(...points);
  const end = Math.max(...points);
  const pad = (end - start) * 0.06 || 86_400_000;
  const pos = (s: string) => ((day(s) - (start - pad)) / (end - start + 2 * pad)) * 100;
  const lang = i18n.language;

  const marks: { at: string; label: string; below?: boolean }[] = [
    { at: baseline, label: t("detail.baseline"), below: true },
    { at: cutoff, label: t("detail.cutoff"), below: true },
    { at: detected, label: t("detail.detected"), below: true },
  ];
  return (
    <div>
      <div className="bracket" data-testid="dated-bracket">
        <div className="axis" />
        {lastClear && <div className="span" style={{ left: `${pos(lastClear)}%`, width: `${Math.max(0.6, pos(firstChanged) - pos(lastClear))}%` }} />}
        {lastClear && (
          <div className="mark" style={{ left: `${pos(lastClear)}%`, transform: "translateX(-100%)" }}>
            {t("detail.last_clear")}
            <b>{fmtDate(lastClear, lang)}</b>
          </div>
        )}
        <div className="mark" style={{ left: `${pos(firstChanged)}%`, transform: "translateX(0)" }}>
          {t("detail.first_changed")}
          <b>{fmtDate(firstChanged, lang)}</b>
        </div>
        {marks.map((m) => (
          <div key={m.label}>
            <div className="tick" style={{ left: `${pos(m.at)}%` }} />
            <div className="mark below" style={{ left: `${pos(m.at)}%` }}>
              {m.label}
              <b>{fmtDate(m.at, lang)}</b>
            </div>
          </div>
        ))}
      </div>
      <p className="small muted" style={{ marginTop: "1.6rem" }}>{t("detail.bracket_note")}</p>
    </div>
  );
}
