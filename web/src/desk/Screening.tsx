/* eslint-disable @typescript-eslint/no-explicit-any */
import { useTranslation } from "react-i18next";
import { api, fmtDate } from "../api";
import { useAsync } from "../components/Bits";

type Run = {
  id: number;
  as_of: string;
  rule_version: string;
  collection: string;
  finished_at: string;
  assets_total: number;
  looks: number | null;
  coverage: Record<string, number> | null;
  outcomes: Record<string, number>;
};

/**
 * The latest weekly screen from space, in one line. Coverage is stated as observed: the screen
 * never says a lake has no change where it had no clear look.
 */
export function ScreeningSummary() {
  const { t, i18n } = useTranslation();
  const { data } = useAsync(() => api<{ items: Run[] }>("/screening/runs?limit=1"), []);
  const run = data?.items?.[0];
  if (!data) return null;
  if (!run) return <p className="note" data-testid="screening-summary">{t("screen.never_run")}</p>;
  const cov = run.coverage ?? {};
  const seen = (cov.no_candidate ?? 0) + (cov.candidate_found ?? 0);
  const unseen = (cov.not_observed ?? 0) + (cov.no_usable_look ?? 0) + (cov.failed ?? 0);
  return (
    <div className="screen-summary" data-testid="screening-summary">
      <b>{t("screen.title", { date: fmtDate(run.as_of, i18n.language) })}</b>
      <span>{t("screen.assets", { count: run.assets_total })}</span>
      <span>{t("screen.looks", { count: run.looks ?? 0 })}</span>
      <span>{t("screen.seen", { count: seen })}</span>
      {cov.candidate_found ? <span className="flag">{t("screen.with_candidates", { count: cov.candidate_found })}</span> : null}
      {unseen > 0 && <span className="flag-overdue">{t("screen.unseen", { count: unseen })}</span>}
      <span className="small muted">{t("screen.source", { rule: run.rule_version })}</span>
    </div>
  );
}

export function CoverageLine({ p }: { p: any }) {
  const { t, i18n } = useTranslation();
  if (!p.screen_status) return <span className="meta"><span className="muted">{t("screen.status.never")}</span></span>;
  return (
    <span className="meta" data-testid="coverage-line">
      <span className={p.screen_status === "candidate_found" ? "flag" : p.screen_status === "no_candidate" ? "" : "flag-overdue"}>
        {t(`screen.status.${p.screen_status}`)}
      </span>
      {p.screen_last_look && <span>{t("screen.last_look", { date: fmtDate(p.screen_last_look, i18n.language) })}</span>}
      <span>{t("screen.looks_since", { count: p.screen_looks ?? 0, date: fmtDate(p.screen_first_look, i18n.language) })}</span>
    </span>
  );
}
