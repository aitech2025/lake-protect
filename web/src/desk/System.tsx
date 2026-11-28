/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { AlertTriangle, CheckCircle2, Cpu, RefreshCw, Workflow, XCircle } from "lucide-react";
import { api, ApiError, fmtDateTime } from "../api";
import { isAdmin, useAuth } from "../auth";
import { useAsync, usePageTitle } from "../components/Bits";
import { EmptyState, PageState, TableRegion } from "../components/PageState";

/** The intelligence registry API (api/app/platform/intelligence_router.py). */
const BASE = "/api/v1/intelligence";
const EVAL_TYPES = ["BACKTEST", "VALIDATION", "SHADOW", "DRIFT", "PRODUCTION"] as const;
const RUN_STATUSES = ["", "QUEUED", "RUNNING", "SUCCEEDED", "PARTIAL", "FAILED", "CANCELLED"];
const errorText = (e: unknown) => (e instanceof ApiError || e instanceof Error ? e.message : String(e));

type Readiness = {
  overall: string; production_ready: boolean; production_certification: string; migration_version: string | null;
  checks: { key: string; status: string; detail: string }[]; production_blockers: string[]; note: string;
};

/**
 * System status (admin): the installation's configuration checklist, the detection models with their
 * evaluations and approvals, and the pipeline's processing runs. Nothing here certifies production
 * readiness; the API says so and so does the page.
 */
export function System() {
  const { t } = useTranslation();
  const { user } = useAuth();
  usePageTitle(t("system.title"));
  if (!isAdmin(user)) return <div className="page"><PageState error="forbidden" status={403} /></div>;
  return (
    <div className="page system" data-testid="system">
      <div className="page-head">
        <div>
          <h1>{t("system.title")}</h1>
          <p className="muted">{t("system.lede")}</p>
        </div>
      </div>
      <ReadinessPanel />
      <Models />
      <Runs />
    </div>
  );
}

function ReadinessPanel() {
  const { t } = useTranslation();
  const { data, error, status, loading, reload } = useAsync(() => api<Readiness>("/readiness"), []);
  return (
    <section aria-labelledby="readiness-title">
      <div className="section-head">
        <h2 className="title-s" id="readiness-title">{t("system.readiness")}</h2>
        <button type="button" className="btn secondary sm" onClick={reload} disabled={loading}><RefreshCw aria-hidden="true" />{t("system.refresh")}</button>
      </div>
      <PageState loading={loading && !data} error={error} status={status} onRetry={reload} />
      {data && (
        <>
          <div className="status-line" data-testid="readiness-overall">
            <span className={`pill ${data.overall === "prototype_ready" ? "ok" : "open"}`}>{t(`system.overall.${data.overall}`, { defaultValue: data.overall })}</span>
            <span className="pill closed">{data.production_ready ? t("system.production_yes") : t("system.production_no")}</span>
            {data.migration_version && <span className="small muted">{t("system.migration")} <code>{data.migration_version}</code></span>}
          </div>
          <div className="check-grid" data-testid="readiness-checks">
            {data.checks.map((c) => {
              const Icon = c.status === "configured" ? CheckCircle2 : c.status === "failed" ? XCircle : AlertTriangle;
              return (
                <div key={c.key} className="check-item" data-status={c.status}>
                  <Icon aria-hidden="true" />
                  <b>{t(`system.check.${c.key}`, { defaultValue: c.key })}</b>
                  <p><span className="sr-only">{t(`system.status.${c.status}`, { defaultValue: c.status })}: </span>{c.detail}</p>
                </div>
              );
            })}
          </div>
          <p className="note" style={{ marginTop: 12 }}>{data.note}</p>
        </>
      )}
    </section>
  );
}

function Models() {
  const { t, i18n } = useTranslation();
  const models = useAsync(() => api<{ items: any[] }>(`${BASE}/models`), []);
  const [selected, setSelected] = useState<string | null>(null);
  const evals = useAsync(() => api<{ items: any[] }>(`${BASE}/evaluations?limit=50${selected ? `&model_version_id=${selected}` : ""}`), [selected]);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const [confirm, setConfirm] = useState<{ id: string; action: "approve" | "promote" } | null>(null);
  const [busy, setBusy] = useState(false);
  const act = async () => {
    if (!confirm) return;
    setBusy(true);
    setMessage(null);
    try {
      await api(`${BASE}/models/${confirm.id}/${confirm.action}`, { method: "POST" });
      setMessage({ ok: true, text: t(`system.${confirm.action}_done`) });
      models.reload();
      evals.reload();
    } catch (err) {
      setMessage({ ok: false, text: errorText(err) });
    } finally {
      setBusy(false);
      setConfirm(null);
    }
  };
  const chosen = models.data?.items.find((m) => m.id === selected);
  return (
    <section className="section" aria-labelledby="models-title">
      <div className="section-head">
        <h2 className="title-s" id="models-title">{t("system.models")}</h2>
        <span className="small muted">{t("system.models_help")}</span>
      </div>
      {message && <p className={`banner ${message.ok ? "info" : "stop"}`} role={message.ok ? "status" : "alert"} style={{ marginBottom: 12 }}>{message.text}</p>}
      <PageState loading={models.loading && !models.data} error={models.error} status={models.status} onRetry={models.reload} />
      {models.data && models.data.items.length === 0 && <EmptyState icon={<Cpu aria-hidden="true" />} title={t("system.no_models")}>{t("system.no_models_help")}</EmptyState>}
      {models.data && models.data.items.length > 0 && (
        <TableRegion label={t("system.models")}>
          <table className="grid" data-testid="models">
            <thead><tr><th>{t("system.col.model")}</th><th>{t("system.col.task")}</th><th>{t("system.col.status")}</th><th>{t("system.col.schema")}</th><th>{t("system.col.registered")}</th><th>{t("system.col.approved")}</th><th /></tr></thead>
            <tbody>
              {models.data.items.map((m) => (
                <tr key={m.id}>
                  <td><button type="button" className="row-open" onClick={() => setSelected(m.id === selected ? null : m.id)} aria-pressed={m.id === selected}>{m.model_name}</button> <span className="mono small muted">{m.model_version}</span></td>
                  <td>{m.task_type}</td>
                  <td><span className={`pill ${m.status === "PRODUCTION" || m.status === "APPROVED" ? "ok" : m.status === "REJECTED" || m.status === "RETIRED" ? "closed" : "review"}`}>{m.status}</span></td>
                  <td className="mono">{m.feature_schema_version}</td>
                  <td className="mono">{fmtDateTime(m.created_at, i18n.language)}</td>
                  <td className="mono">{m.approved_at ? fmtDateTime(m.approved_at, i18n.language) : "–"}</td>
                  <td>
                    <div className="sat-actions">
                      {["REGISTERED", "VALIDATING"].includes(m.status) && <button type="button" className="btn secondary sm" onClick={() => setConfirm({ id: m.id, action: "approve" })}>{t("system.approve")}</button>}
                      {m.status === "APPROVED" && <button type="button" className="btn secondary sm" onClick={() => setConfirm({ id: m.id, action: "promote" })}>{t("system.promote")}</button>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableRegion>
      )}
      {confirm && (
        <div className="banner warn" role="alertdialog" aria-labelledby="confirm-text" style={{ marginTop: 12, display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center", justifyContent: "space-between" }}>
          <span id="confirm-text">{t(`system.${confirm.action}_confirm`)}</span>
          <span className="form-actions">
            <button type="button" className="btn sm" disabled={busy} onClick={() => void act()}>{t(`system.${confirm.action}`)}</button>
            <button type="button" className="btn secondary sm" onClick={() => setConfirm(null)}>{t("action.cancel")}</button>
          </span>
        </div>
      )}
      {chosen && <EvaluationForm modelId={chosen.id} name={`${chosen.model_name} ${chosen.model_version}`} onDone={() => { evals.reload(); models.reload(); }} />}
      <div className="section">
        <div className="section-head">
          <h3 className="title-xs">{chosen ? t("system.evaluations_for", { name: `${chosen.model_name} ${chosen.model_version}` }) : t("system.evaluations")}</h3>
          {chosen && <button type="button" className="btn quiet" onClick={() => setSelected(null)}>{t("system.all_models")}</button>}
        </div>
        <PageState loading={evals.loading && !evals.data} error={evals.error} status={evals.status} onRetry={evals.reload} />
        {evals.data && evals.data.items.length === 0 && <p className="muted small">{t("system.no_evaluations")}</p>}
        {evals.data && evals.data.items.length > 0 && (
          <TableRegion label={t("system.evaluations")}>
            <table className="grid" data-testid="evaluations">
              <thead><tr><th>{t("system.col.type")}</th><th>{t("system.col.dataset")}</th><th>{t("system.col.result")}</th><th>{t("system.col.evaluator")}</th><th>{t("system.col.when")}</th><th>{t("system.col.notes")}</th></tr></thead>
              <tbody>
                {evals.data.items.map((e) => (
                  <tr key={e.id}>
                    <td>{e.evaluation_type}</td>
                    <td className="mono">{e.dataset_ref}</td>
                    <td><span className={`pill ${e.passed ? "ok" : "open"}`}>{e.passed ? t("system.passed") : t("system.failed")}</span></td>
                    <td>{e.evaluator}</td>
                    <td className="mono">{fmtDateTime(e.evaluated_at, i18n.language)}</td>
                    <td>{e.notes ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableRegion>
        )}
      </div>
    </section>
  );
}

function EvaluationForm({ modelId, name, onDone }: { modelId: string; name: string; onDone: () => void }) {
  const { t } = useTranslation();
  const [f, setF] = useState({ evaluation_type: "VALIDATION", dataset_ref: "", metrics: "{\n  \n}", passed: false, notes: "" });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  let metrics: unknown = null;
  try { metrics = JSON.parse(f.metrics); } catch { metrics = null; }
  const valid = !!f.dataset_ref.trim() && metrics !== null && typeof metrics === "object" && !Array.isArray(metrics);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      await api(`${BASE}/models/${modelId}/evaluations`, { json: { evaluation_type: f.evaluation_type, dataset_ref: f.dataset_ref, metrics, passed: f.passed, notes: f.notes || null } });
      setMessage({ ok: true, text: t("system.evaluation_saved") });
      onDone();
    } catch (err) {
      setMessage({ ok: false, text: errorText(err) });
    } finally {
      setBusy(false);
    }
  };
  return (
    <details className="panel flat section" data-testid="evaluation-form">
      <summary className="title-xs" style={{ cursor: "pointer" }}>{t("system.record_evaluation", { name })}</summary>
      <form className="form-grid" style={{ marginTop: 12 }} onSubmit={(e) => void submit(e)}>
        <label className="field">{t("system.col.type")}
          <select value={f.evaluation_type} onChange={(e) => setF({ ...f, evaluation_type: e.target.value })}>{EVAL_TYPES.map((x) => <option key={x}>{x}</option>)}</select>
        </label>
        <label className="field">{t("system.col.dataset")}<input required maxLength={500} value={f.dataset_ref} onChange={(e) => setF({ ...f, dataset_ref: e.target.value })} /></label>
        <label className="field wide">{t("system.metrics")}<textarea rows={4} className="mono" value={f.metrics} onChange={(e) => setF({ ...f, metrics: e.target.value })} aria-invalid={metrics === null} /><small>{t("system.metrics_help")}</small></label>
        <label className="field wide">{t("system.col.notes")}<textarea rows={2} maxLength={4000} value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} /></label>
        <label className="check wide"><input type="checkbox" checked={f.passed} onChange={(e) => setF({ ...f, passed: e.target.checked })} />{t("system.passed_label")}</label>
        {message && <p className={`banner wide ${message.ok ? "info" : "stop"}`} role={message.ok ? "status" : "alert"}>{message.text}</p>}
        <div className="form-actions wide"><button className="btn" disabled={busy || !valid}>{t("system.save_evaluation")}</button></div>
      </form>
    </details>
  );
}

function Runs() {
  const { t, i18n } = useTranslation();
  const [state, setState] = useState("");
  const { data, error, status, loading, reload } = useAsync(() => api<{ items: any[] }>(`${BASE}/processing-runs?limit=50${state ? `&status=${state}` : ""}`), [state]);
  return (
    <section className="section" aria-labelledby="runs-title">
      <div className="section-head">
        <h2 className="title-s" id="runs-title">{t("system.runs")}</h2>
        <label className="field" style={{ minWidth: 180 }}>
          {t("system.col.status")}
          <select value={state} onChange={(e) => setState(e.target.value)}>{RUN_STATUSES.map((s) => <option key={s} value={s}>{s || t("group.all")}</option>)}</select>
        </label>
      </div>
      <PageState loading={loading && !data} error={error} status={status} onRetry={reload} />
      {data && data.items.length === 0 && <EmptyState icon={<Workflow aria-hidden="true" />} title={t("system.no_runs")}>{t("system.no_runs_help")}</EmptyState>}
      {data && data.items.length > 0 && (
        <TableRegion label={t("system.runs")}>
          <table className="grid" data-testid="processing-runs">
            <thead><tr><th>{t("system.col.pipeline")}</th><th>{t("system.col.status")}</th><th className="num">{t("system.col.attempt")}</th><th>{t("system.col.started")}</th><th>{t("system.col.finished")}</th><th>{t("system.col.error")}</th><th>{t("system.col.correlation")}</th></tr></thead>
            <tbody>
              {data.items.map((r) => (
                <tr key={r.id}>
                  <td>{r.pipeline_name} <span className="mono small muted">{r.pipeline_version}</span></td>
                  <td><span className={`pill ${r.status === "SUCCEEDED" ? "ok" : r.status === "FAILED" ? "open" : "review"}`}>{r.status}</span></td>
                  <td className="num">{r.attempt}</td>
                  <td className="mono">{r.started_at ? fmtDateTime(r.started_at, i18n.language) : "–"}</td>
                  <td className="mono">{r.finished_at ? fmtDateTime(r.finished_at, i18n.language) : "–"}</td>
                  <td className="mono">{r.error_code ?? ""}</td>
                  <td className="mono small">{r.correlation_id ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableRegion>
      )}
    </section>
  );
}
