import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api, fmtDateTime } from "../api";
import { useAuth } from "../auth";
import { useAsync, usePageTitle } from "../components/Bits";
import { PageState, TableRegion } from "../components/PageState";

type Dataset = { dataset: string; file_name: string; format: string; required: boolean; fields: string[]; optional_fields: string[]; description: string };
type RunSummary = { id: number; connector: string; transport: string; is_sample: boolean; finished_at: string; counts: Record<string, number> };
type Source = {
  name: string;
  agency: string;
  summary: string;
  datasets: Dataset[];
  agreement_ref: string | null;
  api_configured: boolean;
  drop_folder: string;
  files_waiting: string[];
  sample_available: boolean;
  last_run: RunSummary | null;
};
type Item = { action: string; ref: string; asset_key?: string; reason?: string; status?: string; cohort_after?: string };
type Report = {
  run_id: number | null;
  connector: string;
  agency: string;
  transport: string;
  is_sample: boolean;
  dry_run: boolean;
  counts: Record<string, number>;
  items: Item[];
  snapshots: { dataset: string; file_name: string; sha256: string; stripped_fields: string[]; reused: boolean }[];
};

function Counts({ counts }: { counts: Record<string, number> }) {
  const { t } = useTranslation();
  const entries = Object.entries(counts);
  if (!entries.length) return <span className="muted">{t("sources.nothing")}</span>;
  return (
    <span className="meta">
      {entries.map(([k, n]) => (
        <span key={k} className={["conflicts", "rejected"].includes(k) ? "flag" : undefined}>{t(`sources.count.${k}`, { count: n })}</span>
      ))}
    </span>
  );
}

function ReportView({ report }: { report: Report }) {
  const { t } = useTranslation();
  return (
    <section className="section" data-testid="source-report" aria-live="polite">
      <h2>{report.dry_run ? t("sources.preview_of", { agency: report.agency }) : t("sources.loaded", { agency: report.agency, id: report.run_id })}</h2>
      <p className={`banner ${report.dry_run ? "info" : "warn"}`} style={{ marginBottom: "0.75rem" }}>
        {report.dry_run ? t("sources.preview_note") : t("sources.loaded_note")}
        {report.is_sample ? ` ${t("sources.sample_note")}` : ""}
      </p>
      <Counts counts={report.counts} />
      <TableRegion label={t("sources.records")}>
        <table className="grid" style={{ marginTop: "0.75rem" }}>
          <thead><tr><th>{t("sources.col.action")}</th><th>{t("sources.col.record")}</th><th>{t("sources.col.asset")}</th><th>{t("sources.col.why")}</th></tr></thead>
          <tbody>
            {report.items.map((i, n) => (
              <tr key={n} data-action={i.action}>
                <td className={["conflict", "rejected"].includes(i.action) ? "flag" : undefined}>{t(`sources.action.${i.action}`)}</td>
                <td><code>{i.ref}</code></td>
                <td>{i.asset_key ?? ""}{i.cohort_after ? <div className="small muted">{t(`cohort.${i.cohort_after}`)}</div> : null}</td>
                <td>{i.reason ?? (i.status ? t(`boundary.${i.status}`) : "")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableRegion>
      <p className="small muted" style={{ marginTop: "0.5rem" }}>
        {report.snapshots.map((s) => `${s.file_name} · SHA-256 ${s.sha256.slice(0, 12)}…${s.reused ? ` (${t("sources.seen_before")})` : ""}`).join("  ·  ")}
      </p>
    </section>
  );
}

/**
 * Government sources and the asset creation engine (docs/asset-engine.md). No data-sharing
 * agreement exists yet, so sources load from files: an officer's drop folder or the fictional samples.
 */
export function Sources() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const { user } = useAuth();
  const canRun = user?.role === "admin";
  const { data, error, status, loading, reload } = useAsync(() => api<{ items: Source[] }>("/sources"), []);
  const runs = useAsync(() => api<{ items: RunSummary[] }>("/sources/runs?limit=10"), []);
  const [report, setReport] = useState<Report | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  usePageTitle(t("sources.title"));

  const start = async (name: string, transport: string, dryRun: boolean) => {
    setBusy(`${name}:${transport}:${dryRun}`);
    setMessage(null);
    try {
      const out = await api<Report>(`/sources/${name}/runs`, { json: { transport, dry_run: dryRun } });
      setReport(out);
      if (!dryRun) {
        reload();
        runs.reload();
      }
    } catch (e) {
      setReport(null);
      setMessage((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const button = (s: Source, transport: string, dryRun: boolean, label: string) => (
    <button
      type="button"
      className={dryRun ? "btn secondary" : "btn"}
      disabled={busy !== null}
      data-testid={`run-${s.name}-${transport}-${dryRun ? "preview" : "apply"}`}
      onClick={() => void start(s.name, transport, dryRun)}
    >
      {busy === `${s.name}:${transport}:${dryRun}` ? t("sources.running") : label}
    </button>
  );

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>{t("sources.title")}</h1>
          <p className="muted">{t("sources.lede")}</p>
        </div>
      </div>
      <p className="note" style={{ marginBottom: "1rem" }}>{t("sources.no_agreement")}</p>
      <PageState loading={loading && !data} error={error} status={status} onRetry={reload} />
      {message && <p className="banner stop" role="alert" style={{ marginBottom: "1rem" }}>{message}</p>}
      <div className="source-grid">
        {data?.items.map((s) => (
          <section key={s.name} className="source-card" data-testid={`source-${s.name}`}>
            <h2>{s.agency}</h2>
            <p className="muted small">{s.summary}</p>
            <dl className="kv">
              <dt>{t("sources.agreement")}</dt>
              <dd>{s.agreement_ref ?? <span className="flag">{t("sources.none_yet")}</span>}</dd>
              <dt>{t("sources.drop")}</dt>
              <dd><code>{s.drop_folder}</code><div className="small muted">{s.files_waiting.length ? s.files_waiting.join(", ") : t("sources.no_files")}</div></dd>
              <dt>{t("sources.last_run")}</dt>
              <dd>{s.last_run ? <>{fmtDateTime(s.last_run.finished_at, lang)} · {t(`sources.via.${s.last_run.transport}`)}<div><Counts counts={s.last_run.counts} /></div></> : t("sources.never")}</dd>
            </dl>
            <details>
              <summary>{t("sources.contract")}</summary>
              <ul className="contract">
                {s.datasets.map((d) => (
                  <li key={d.dataset}>
                    <code>{d.file_name}</code> {d.required ? <b>{t("sources.required")}</b> : <span className="muted">{t("sources.optional")}</span>}
                    <div className="small">{d.description}</div>
                    <div className="small muted">{d.fields.join(", ")}{d.optional_fields.length ? ` · ${t("sources.optional")}: ${d.optional_fields.join(", ")}` : ""}</div>
                  </li>
                ))}
              </ul>
            </details>
            {canRun && (
              <div className="source-actions">
                {s.sample_available && button(s, "sample", true, t("sources.preview_sample"))}
                {s.sample_available && button(s, "sample", false, t("sources.load_sample"))}
                {s.files_waiting.length > 0 && button(s, "file_drop", true, t("sources.preview_drop"))}
                {s.files_waiting.length > 0 && button(s, "file_drop", false, t("sources.load_drop"))}
              </div>
            )}
          </section>
        ))}
      </div>
      {report && <ReportView report={report} />}
      <section className="section">
        <h2>{t("sources.recent")}</h2>
        {runs.data && runs.data.items.length === 0 && <p className="muted">{t("sources.no_runs")}</p>}
        {runs.data && runs.data.items.length > 0 && (
          <TableRegion label={t("sources.recent")}>
            <table className="grid" data-testid="import-runs">
              <thead><tr><th>#</th><th>{t("sources.col.when")}</th><th>{t("sources.col.source")}</th><th>{t("sources.col.result")}</th></tr></thead>
              <tbody>
                {runs.data.items.map((r) => (
                  <tr key={r.id}>
                    <td>{r.id}</td>
                    <td>{fmtDateTime(r.finished_at, lang)}</td>
                    <td>{r.connector} · {t(`sources.via.${r.transport}`)}</td>
                    <td><Counts counts={r.counts} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableRegion>
        )}
      </section>
    </div>
  );
}
