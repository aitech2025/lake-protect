/* eslint-disable @typescript-eslint/no-explicit-any */
import { useMemo, useState, type FormEvent, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Building2, Landmark, MapPinned, Plus } from "lucide-react";
import { api, ApiError, fmtDate, fmtDateTime } from "../api";
import { isAdmin, useAuth } from "../auth";
import { useAsync, usePageTitle } from "../components/Bits";
import { Drawer } from "../components/Drawer";
import { MapView } from "../components/MapView";
import { EmptyState, PageState, TableRegion } from "../components/PageState";
import { Segmented } from "../components/Segmented";

/** The statewide registry API (api/app/platform/router.py). */
const BASE = "/api/v1/platform";
const AUTHORITY = ["AUTHORITATIVE", "CERTIFIED", "DERIVED", "EXTERNAL", "FIELD", "MODEL", "UNVERIFIED"] as const;
const RELATIONSHIPS = ["OWNER", "CUSTODIAN", "POSSESSOR", "JURISDICTION", "OPERATIONAL", "ENFORCEMENT", "DATA_STEWARD"] as const;
const ACCESS = ["READ", "CONTRIBUTE", "MANAGE"] as const;
const PAGE = 100;
type Tab = "assets" | "candidates" | "departments";
const TABS: Tab[] = ["assets", "candidates", "departments"];

type RegAsset = { id: string; asset_code: string; display_name: string; category_code: string; lifecycle_status: string; baseline_date: string | null; source_authority: string };
type Department = { id: string; code: string; name: string; parent_id: string | null; is_active: boolean };
type Candidate = {
  id: string; candidate_code: string; display_name: string; category_hint: string | null; district: string | null; mandal: string | null; village: string | null;
  status: string; created_at: string; source_report_ref: string; detection_candidate_id: number | null; incident_id: number | null; footprint: GeoJSON.Geometry | null;
};

const today = () => new Date().toISOString().slice(0, 10);
const errorText = (e: unknown) => (e instanceof ApiError || e instanceof Error ? e.message : String(e));

/** Source authority, drawn in the boundary line language: solid is official, dashed derived, dotted unverified. */
export function Authority({ value }: { value: string }) {
  const { t } = useTranslation();
  return <span className="authority" data-class={value}>{t(`registry.authority.${value}`, { defaultValue: value })}</span>;
}

function footprintFc(geometry: GeoJSON.Geometry | null | undefined, kind = "parcel"): GeoJSON.FeatureCollection {
  return { type: "FeatureCollection", features: geometry ? [{ type: "Feature", properties: { kind, status: "" }, geometry }] : [] };
}

/**
 * The statewide registry (D-055 onward): registered public assets with their permanent codes, the
 * departments responsible for them, and reported places that are not assets until verified.
 * Everything here reads and writes through the registry API; the admin's changes are audited there.
 */
export function Registry() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const tab = (TABS.includes(params.get("tab") as Tab) ? params.get("tab") : "assets") as Tab;
  const departments = useAsync(() => api<{ items: Department[] }>(`${BASE}/departments`), []);
  usePageTitle(t("registry.title"));
  return (
    <div className="page registry" data-testid="registry">
      <div className="page-head">
        <div>
          <h1>{t("registry.title")}</h1>
          <p className="muted">{t("registry.lede")}</p>
        </div>
      </div>
      <div className="section-head" style={{ marginBottom: 20 }}>
        <Segmented
          mode="tabs"
          label={t("registry.sections")}
          value={tab}
          onChange={(v) => setParams({ tab: v })}
          options={TABS.map((v) => ({ value: v, label: t(`registry.tab.${v}`), testId: `registry-tab-${v}` }))}
        />
      </div>
      {tab === "assets" && <RegisteredAssets departments={departments.data?.items ?? []} />}
      {tab === "candidates" && <Candidates />}
      {tab === "departments" && <Departments list={departments} />}
    </div>
  );
}

function RegisteredAssets({ departments }: { departments: Department[] }) {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const [category, setCategory] = useState("");
  const [term, setTerm] = useState("");
  const [limit, setLimit] = useState(PAGE);
  const [open, setOpen] = useState<RegAsset | null>(null);
  const [adding, setAdding] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const q = new URLSearchParams({ limit: String(Math.min(limit, 500)) });
  if (category) q.set("category", category);
  const { data, error, status, loading, reload } = useAsync(() => api<{ items: RegAsset[] }>(`${BASE}/assets?${q}`), [category, limit]);
  const seen = useAsync(() => api<{ items: RegAsset[] }>(`${BASE}/assets?limit=500`), []);
  const categories = useMemo(() => Array.from(new Set((seen.data?.items ?? []).map((a) => a.category_code))).sort(), [seen.data]);
  const needle = term.trim().toLocaleLowerCase();
  const rows = (data?.items ?? []).filter((a) => !needle || [a.asset_code, a.display_name].some((v) => v.toLocaleLowerCase().includes(needle)));
  return (
    <>
      <div className="toolbar">
        <div className="toolbar-row">
          <label className="field">{t("registry.search")}<input type="search" value={term} onChange={(e) => setTerm(e.target.value)} placeholder={t("registry.search_hint")} data-testid="registry-search" /></label>
          <label className="field">{t("registry.category")}
            <select value={category} onChange={(e) => { setCategory(e.target.value); setLimit(PAGE); }} data-testid="registry-category">
              <option value="">{t("group.all")}</option>
              {categories.map((c) => <option key={c} value={c}>{t(`registry.category_name.${c}`, { defaultValue: c })}</option>)}
            </select>
          </label>
          <span className="spacer" />
          {isAdmin(user) && <button type="button" className="btn" onClick={() => setAdding(true)} data-testid="registry-add"><Plus aria-hidden="true" />{t("registry.add_asset")}</button>}
        </div>
      </div>
      {notice && <p className="banner info" role="status" style={{ marginBottom: 16 }}>{notice}</p>}
      <PageState loading={loading && !data} error={error} status={status} onRetry={reload} />
      {data && rows.length === 0 && <EmptyState icon={<Landmark aria-hidden="true" />} title={t("registry.no_assets")} />}
      {rows.length > 0 && (
        <TableRegion label={t("registry.tab.assets")}>
          <table className="grid" data-testid="registry-assets">
            <thead>
              <tr><th>{t("registry.col.code")}</th><th>{t("registry.col.name")}</th><th>{t("registry.category")}</th><th>{t("registry.col.authority")}</th><th>{t("registry.col.lifecycle")}</th><th>{t("registry.col.baseline")}</th></tr>
            </thead>
            <tbody>
              {rows.map((a) => (
                <tr key={a.id} className="clickable" onClick={() => setOpen(a)}>
                  <td className="mono"><button type="button" className="row-open" onClick={(e) => { e.stopPropagation(); setOpen(a); }}>{a.asset_code}</button></td>
                  <td>{a.display_name}</td>
                  <td>{t(`registry.category_name.${a.category_code}`, { defaultValue: a.category_code })}</td>
                  <td><Authority value={a.source_authority} /></td>
                  <td><span className={`pill ${a.lifecycle_status === "ACTIVE" ? "ok" : "closed"}`}>{t(`registry.lifecycle.${a.lifecycle_status}`, { defaultValue: a.lifecycle_status })}</span></td>
                  <td className="mono">{a.baseline_date ? fmtDate(a.baseline_date, i18n.language) : "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableRegion>
      )}
      <div className="list-foot">
        <span className="small muted">{t("registry.showing", { n: rows.length })}</span>
        {data && data.items.length >= limit && limit < 500 && <button type="button" className="btn secondary sm" onClick={() => setLimit((n) => n + PAGE)}>{t("registry.more")}</button>}
      </div>
      <Drawer open={!!open} onClose={() => setOpen(null)} title={open?.display_name} subtitle={<span className="mono">{open?.asset_code}</span>} testId="registry-asset">
        {open && <AssetDetail id={open.id} departments={departments} />}
      </Drawer>
      <Drawer open={adding} onClose={() => setAdding(false)} title={t("registry.add_asset")} subtitle={t("registry.add_asset_help")}>
        <AddAssetForm onDone={(a) => { setAdding(false); setNotice(t("registry.asset_added", { code: a.asset_code })); reload(); seen.reload(); }} />
      </Drawer>
    </>
  );
}

function AssetDetail({ id, departments }: { id: string; departments: Department[] }) {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const asset = useAsync(() => api<any>(`${BASE}/assets/${id}`), [id]);
  const resp = useAsync(() => api<{ items: any[] }>(`${BASE}/assets/${id}/responsibilities`), [id]);
  const deptName = (depId: string) => departments.find((d) => d.id === depId)?.name ?? depId;
  const a = asset.data;
  const fc = useMemo(() => footprintFc(a?.footprint), [a]);
  return (
    <>
      <PageState loading={asset.loading && !a} error={asset.error} status={asset.status} onRetry={asset.reload} />
      {a && (
        <>
          <dl className="facts">
            <dt>{t("registry.col.code")}</dt><dd className="mono">{a.asset_code}</dd>
            <dt>{t("registry.category")}</dt><dd>{t(`registry.category_name.${a.category_code}`, { defaultValue: a.category_code })}</dd>
            <dt>{t("registry.col.lifecycle")}</dt><dd>{t(`registry.lifecycle.${a.lifecycle_status}`, { defaultValue: a.lifecycle_status })}</dd>
            <dt>{t("registry.col.baseline")}</dt><dd>{a.baseline_date ? fmtDate(a.baseline_date, i18n.language) : "–"}</dd>
            <dt>{t("registry.col.authority")}</dt><dd><Authority value={a.source_authority} /></dd>
            <dt>{t("registry.source_ref")}</dt><dd>{a.source_record_ref ? <code>{a.source_record_ref}</code> : <span className="muted">{t("registry.none")}</span>}</dd>
          </dl>
          {a.footprint ? (
            <div className="mapbox" style={{ height: 240 }}><MapView boundaries={fc} testId="registry-footprint" /></div>
          ) : <p className="note">{t("registry.no_footprint")}</p>}
        </>
      )}
      <section>
        <h3 className="title-xs" style={{ marginBottom: 8 }}>{t("registry.responsibilities")}</h3>
        <PageState error={resp.error} status={resp.status} onRetry={resp.reload} />
        {resp.data && resp.data.items.length === 0 && <p className="muted small">{t("registry.no_responsibilities")}</p>}
        {resp.data && resp.data.items.length > 0 && (
          <ul className="officer-list" data-testid="registry-responsibilities">
            {resp.data.items.map((r) => (
              <li key={r.id}>
                <b>{t(`registry.relationship.${r.relationship_type}`, { defaultValue: r.relationship_type })}: {deptName(r.department_id)}</b>
                <span className="small muted">{t("registry.valid", { from: fmtDate(r.valid_from, i18n.language), to: r.valid_to ? fmtDate(r.valid_to, i18n.language) : t("registry.open_ended") })}</span>
                <span className="small"><Authority value={r.source_authority} /> <code>{r.source_record_ref}</code></span>
              </li>
            ))}
          </ul>
        )}
      </section>
      {isAdmin(user) && <ResponsibilityForm assetId={id} departments={departments} onDone={resp.reload} />}
    </>
  );
}

function ResponsibilityForm({ assetId, departments, onDone }: { assetId: string; departments: Department[]; onDone: () => void }) {
  const { t } = useTranslation();
  const [f, setF] = useState({ department_id: "", relationship_type: "CUSTODIAN", valid_from: today(), valid_to: "", source_authority: "UNVERIFIED", source_record_ref: "" });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF((x) => ({ ...x, [k]: e.target.value }));
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      await api(`${BASE}/assets/${assetId}/responsibilities`, { json: { ...f, valid_to: f.valid_to || null } });
      setMessage({ ok: true, text: t("registry.responsibility_added") });
      setF((x) => ({ ...x, source_record_ref: "", valid_to: "" }));
      onDone();
    } catch (err) {
      setMessage({ ok: false, text: errorText(err) });
    } finally {
      setBusy(false);
    }
  };
  if (!departments.length) return <p className="note">{t("registry.need_department")}</p>;
  return (
    <form className="officer-form" onSubmit={(e) => void submit(e)} data-testid="responsibility-form">
      <h3 className="title-xs">{t("registry.add_responsibility")}</h3>
      <div className="form-grid">
        <label className="field">{t("registry.department")}
          <select required value={f.department_id} onChange={set("department_id")}>
            <option value="">{t("registry.choose")}</option>
            {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </label>
        <label className="field">{t("registry.relationship_label")}
          <select value={f.relationship_type} onChange={set("relationship_type")}>
            {RELATIONSHIPS.map((r) => <option key={r} value={r}>{t(`registry.relationship.${r}`)}</option>)}
          </select>
        </label>
        <label className="field">{t("registry.valid_from")}<input type="date" required value={f.valid_from} onChange={set("valid_from")} /></label>
        <label className="field">{t("registry.valid_to")}<input type="date" value={f.valid_to} min={f.valid_from} onChange={set("valid_to")} /></label>
        <label className="field">{t("registry.col.authority")}
          <select value={f.source_authority} onChange={set("source_authority")}>
            {AUTHORITY.map((a) => <option key={a} value={a}>{t(`registry.authority.${a}`)}</option>)}
          </select>
        </label>
        <label className="field">{t("registry.source_ref")}<input required maxLength={500} value={f.source_record_ref} onChange={set("source_record_ref")} /></label>
      </div>
      {message && <p className={`banner ${message.ok ? "info" : "stop"}`} role={message.ok ? "status" : "alert"}>{message.text}</p>}
      <div className="form-actions"><button className="btn" disabled={busy || !f.department_id || !f.source_record_ref.trim()}>{t("registry.record_responsibility")}</button></div>
    </form>
  );
}

function AddAssetForm({ onDone }: { onDone: (a: RegAsset) => void }) {
  const { t } = useTranslation();
  const [f, setF] = useState({ asset_code: "", display_name: "", category_code: "", baseline_date: "", source_authority: "UNVERIFIED", source_record_ref: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF((x) => ({ ...x, [k]: e.target.value }));
  const needsRef = f.source_authority === "AUTHORITATIVE" || f.source_authority === "CERTIFIED";
  const reported = f.category_code.trim().toLocaleLowerCase() === "reported_place";
  const codeOk = /^[A-Za-z0-9._-]{2,80}$/.test(f.asset_code);
  const ready = codeOk && f.display_name.trim().length >= 2 && f.category_code.trim().length >= 2 && !reported && (!needsRef || f.source_record_ref.trim());
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const out = await api<RegAsset>(`${BASE}/assets`, { json: { ...f, baseline_date: f.baseline_date || null, source_record_ref: f.source_record_ref.trim() || null } });
      onDone(out);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };
  return (
    <form className="form-grid" onSubmit={(e) => void submit(e)} data-testid="registry-add-form">
      <label className="field">{t("registry.col.code")}<input required value={f.asset_code} onChange={set("asset_code")} pattern="[A-Za-z0-9._\-]+" maxLength={80} aria-invalid={!!f.asset_code && !codeOk} /><small>{t("registry.code_help")}</small></label>
      <label className="field">{t("registry.category")}<input required value={f.category_code} onChange={set("category_code")} maxLength={80} aria-invalid={reported} /><small>{reported ? t("registry.reported_place") : t("registry.category_help")}</small></label>
      <label className="field wide">{t("registry.col.name")}<input required value={f.display_name} onChange={set("display_name")} maxLength={240} /></label>
      <label className="field">{t("registry.col.baseline")}<input type="date" value={f.baseline_date} onChange={set("baseline_date")} /></label>
      <label className="field">{t("registry.col.authority")}
        <select value={f.source_authority} onChange={set("source_authority")}>
          {AUTHORITY.map((a) => <option key={a} value={a}>{t(`registry.authority.${a}`)}</option>)}
        </select>
      </label>
      <label className="field wide">{t("registry.source_ref")}<input value={f.source_record_ref} onChange={set("source_record_ref")} maxLength={500} required={needsRef} /><small>{needsRef ? t("registry.ref_required") : t("registry.ref_optional")}</small></label>
      {error && <p className="banner stop wide" role="alert">{error}</p>}
      <div className="form-actions wide"><button className="btn" disabled={busy || !ready}>{t("registry.create_asset")}</button></div>
    </form>
  );
}

function Candidates() {
  const { t, i18n } = useTranslation();
  const [offset, setOffset] = useState(0);
  const [open, setOpen] = useState<Candidate | null>(null);
  const { data, error, status, loading, reload } = useAsync(() => api<{ items: Candidate[]; notice: string }>(`${BASE}/candidate-assets?limit=${PAGE}&offset=${offset}`), [offset]);
  const place = (c: Candidate) => [c.village, c.mandal, c.district].filter(Boolean).join(", ") || t("dashboard.not_recorded");
  return (
    <>
      <p className="banner warn" style={{ marginBottom: 16 }} data-testid="candidate-notice">{t("registry.candidate_notice")}</p>
      <PageState loading={loading && !data} error={error} status={status} onRetry={reload} />
      {data && data.items.length === 0 && <EmptyState icon={<MapPinned aria-hidden="true" />} title={t("registry.no_candidates")}>{t("registry.no_candidates_help")}</EmptyState>}
      {data && data.items.length > 0 && (
        <TableRegion label={t("registry.tab.candidates")}>
          <table className="grid" data-testid="registry-candidates">
            <thead>
              <tr><th>{t("registry.col.candidate")}</th><th>{t("registry.col.hint")}</th><th>{t("registry.col.place")}</th><th>{t("registry.col.status")}</th><th>{t("registry.col.reported")}</th><th>{t("registry.col.incident")}</th></tr>
            </thead>
            <tbody>
              {data.items.map((c) => (
                <tr key={c.id} className="clickable" onClick={() => setOpen(c)}>
                  <td><button type="button" className="row-open mono" onClick={(e) => { e.stopPropagation(); setOpen(c); }}>{c.candidate_code}</button></td>
                  <td>{c.category_hint ? t(`reports.what.${c.category_hint}`, { defaultValue: c.category_hint }) : "–"}</td>
                  <td>{place(c)}</td>
                  <td><span className="pill review">{t(`registry.candidate_status.${c.status}`, { defaultValue: c.status })}</span></td>
                  <td className="mono">{fmtDate(c.created_at, i18n.language)}</td>
                  <td>{c.incident_id ? <Link to={`/alerts/${c.incident_id}`} onClick={(e) => e.stopPropagation()}>{t("registry.open_incident")}</Link> : "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableRegion>
      )}
      {data && (
        <div className="list-foot">
          {offset > 0 && <button type="button" className="btn secondary sm" onClick={() => setOffset((n) => Math.max(0, n - PAGE))}>{t("registry.previous")}</button>}
          {data.items.length >= PAGE && <button type="button" className="btn secondary sm" onClick={() => setOffset((n) => n + PAGE)}>{t("registry.next")}</button>}
        </div>
      )}
      <Drawer open={!!open} onClose={() => setOpen(null)} title={open?.display_name} subtitle={<span className="mono">{open?.candidate_code}</span>} testId="candidate-detail">
        {open && <CandidateDetail c={open} />}
      </Drawer>
    </>
  );
}

function CandidateDetail({ c }: { c: Candidate }) {
  const { t, i18n } = useTranslation();
  const changes = useMemo(() => footprintFc(c.footprint), [c]);
  const preds = useAsync(() => (c.detection_candidate_id ? api<{ items: any[] }>(`${BASE}/candidates/${c.detection_candidate_id}/predictions`) : Promise.resolve({ items: [] })), [c.detection_candidate_id]);
  return (
    <>
      <p className="note">{t("registry.candidate_notice")}</p>
      <dl className="facts">
        <dt>{t("registry.col.status")}</dt><dd>{t(`registry.candidate_status.${c.status}`, { defaultValue: c.status })}</dd>
        <dt>{t("registry.col.hint")}</dt><dd>{c.category_hint ? t(`reports.what.${c.category_hint}`, { defaultValue: c.category_hint }) : "–"}</dd>
        <dt>{t("asset360.district")}</dt><dd>{c.district ?? t("dashboard.not_recorded")}</dd>
        <dt>{t("asset360.mandal")}</dt><dd>{c.mandal ?? t("dashboard.not_recorded")}</dd>
        <dt>{t("asset360.village")}</dt><dd>{c.village ?? t("dashboard.not_recorded")}</dd>
        <dt>{t("registry.col.reported")}</dt><dd>{fmtDateTime(c.created_at, i18n.language)}</dd>
        <dt>{t("registry.source_report")}</dt><dd className="mono">{c.source_report_ref}</dd>
      </dl>
      {c.footprint && <div className="mapbox" style={{ height: 240 }}><MapView changes={changes} testId="candidate-footprint" /></div>}
      <div className="form-actions">
        {c.incident_id && <Link className="btn secondary" to={`/alerts/${c.incident_id}`}>{t("registry.open_incident")}</Link>}
      </div>
      <section>
        <h3 className="title-xs" style={{ marginBottom: 8 }}>{t("registry.predictions")}</h3>
        {preds.loading && <PageState loading />}
        {preds.error && <p className="note">{preds.status === 404 ? t("registry.no_prediction") : t("registry.prediction_unavailable", { msg: preds.error })}</p>}
        {preds.data && preds.data.items.length === 0 && !preds.error && <p className="note">{t("registry.no_prediction")}</p>}
        {preds.data && preds.data.items.map((p) => (
          <div key={p.id} className="officer-form">
            <b>{t("registry.prediction_score", { type: p.score_type, score: typeof p.score === "number" ? p.score.toFixed(2) : p.score })}</b>
            <span className="small muted">{p.model_name} {p.model_version}, {fmtDateTime(p.generated_at, i18n.language)}</span>
            {p.disclaimer && <p className="small">{p.disclaimer}</p>}
          </div>
        ))}
      </section>
    </>
  );
}

function Departments({ list }: { list: ReturnType<typeof useAsync<{ items: Department[] }>> }) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const admin = isAdmin(user);
  const { data, error, status, loading, reload } = list;
  const byId = (id: string | null) => (id ? data?.items.find((d) => d.id === id)?.name ?? id : "–");
  return (
    <div className={admin ? "split" : undefined}>
      <div>
        <PageState loading={loading && !data} error={error} status={status} onRetry={reload} />
        {data && data.items.length === 0 && <EmptyState icon={<Building2 aria-hidden="true" />} title={t("registry.no_departments")}>{admin ? t("registry.no_departments_admin") : t("registry.no_departments_viewer")}</EmptyState>}
        {data && data.items.length > 0 && (
          <TableRegion label={t("registry.tab.departments")}>
            <table className="grid" data-testid="registry-departments">
              <thead><tr><th>{t("registry.col.dept_code")}</th><th>{t("registry.col.name")}</th><th>{t("registry.col.parent")}</th></tr></thead>
              <tbody>{data.items.map((d) => <tr key={d.id}><td className="mono">{d.code}</td><td>{d.name}</td><td>{byId(d.parent_id)}</td></tr>)}</tbody>
            </table>
          </TableRegion>
        )}
      </div>
      {admin && (
        <aside style={{ display: "grid", gap: 16 }}>
          <Panel title={t("registry.add_department")}><DepartmentForm departments={data?.items ?? []} onDone={reload} /></Panel>
          {!!data?.items.length && <Panel title={t("registry.access_title")}><AccessForm departments={data.items} /></Panel>}
        </aside>
      )}
    </div>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return <section className="panel"><h2 className="title-s">{title}</h2>{children}</section>;
}

function DepartmentForm({ departments, onDone }: { departments: Department[]; onDone: () => void }) {
  const { t } = useTranslation();
  const [f, setF] = useState({ code: "", name: "", parent_id: "" });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const codeOk = /^[A-Za-z0-9._-]{2,80}$/.test(f.code);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      await api(`${BASE}/departments`, { json: { code: f.code, name: f.name, parent_id: f.parent_id || null } });
      setMessage({ ok: true, text: t("registry.department_added", { name: f.name }) });
      setF({ code: "", name: "", parent_id: "" });
      onDone();
    } catch (err) {
      setMessage({ ok: false, text: errorText(err) });
    } finally {
      setBusy(false);
    }
  };
  return (
    <form className="form-grid" onSubmit={(e) => void submit(e)} data-testid="department-form">
      <label className="field">{t("registry.col.dept_code")}<input required value={f.code} onChange={(e) => setF({ ...f, code: e.target.value })} maxLength={80} aria-invalid={!!f.code && !codeOk} /></label>
      <label className="field">{t("registry.col.parent")}
        <select value={f.parent_id} onChange={(e) => setF({ ...f, parent_id: e.target.value })}>
          <option value="">{t("registry.no_parent")}</option>
          {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
      </label>
      <label className="field wide">{t("registry.col.name")}<input required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} maxLength={240} /></label>
      {message && <p className={`banner wide ${message.ok ? "info" : "stop"}`} role={message.ok ? "status" : "alert"}>{message.text}</p>}
      <div className="form-actions wide"><button className="btn" disabled={busy || !codeOk || f.name.trim().length < 2}>{t("registry.create_department")}</button></div>
    </form>
  );
}

function AccessForm({ departments }: { departments: Department[] }) {
  const { t } = useTranslation();
  const users = useAsync(() => api<{ id: number; name: string; role: string }[]>("/users"), []);
  const [f, setF] = useState({ department: "", user: "", access_level: "READ", valid_from: today() });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const run = async (grant: boolean) => {
    setBusy(true);
    setMessage(null);
    const path = `${BASE}/departments/${f.department}/members/${f.user}`;
    try {
      if (grant) await api(path, { json: { access_level: f.access_level, valid_from: f.valid_from } });
      else await api(path, { method: "DELETE" });
      setMessage({ ok: true, text: t(grant ? "registry.access_granted" : "registry.access_revoked") });
    } catch (err) {
      setMessage({ ok: false, text: errorText(err) });
    } finally {
      setBusy(false);
    }
  };
  const ready = !!f.department && !!f.user;
  return (
    <form className="form-grid" onSubmit={(e) => { e.preventDefault(); void run(true); }} data-testid="access-form">
      <label className="field wide">{t("registry.department")}
        <select required value={f.department} onChange={(e) => setF({ ...f, department: e.target.value })}>
          <option value="">{t("registry.choose")}</option>
          {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
      </label>
      <label className="field wide">{t("registry.user")}
        <select required value={f.user} onChange={(e) => setF({ ...f, user: e.target.value })}>
          <option value="">{t("registry.choose")}</option>
          {(users.data ?? []).map((u) => <option key={u.id} value={u.id}>{u.name} ({t(`role.${u.role}`)})</option>)}
        </select>
      </label>
      <label className="field">{t("registry.access_level")}
        <select value={f.access_level} onChange={(e) => setF({ ...f, access_level: e.target.value })}>
          {ACCESS.map((a) => <option key={a} value={a}>{t(`registry.access.${a}`)}</option>)}
        </select>
      </label>
      <label className="field">{t("registry.valid_from")}<input type="date" value={f.valid_from} onChange={(e) => setF({ ...f, valid_from: e.target.value })} /></label>
      <p className="small muted wide">{t("registry.access_help")}</p>
      {message && <p className={`banner wide ${message.ok ? "info" : "stop"}`} role={message.ok ? "status" : "alert"}>{message.text}</p>}
      <div className="form-actions wide">
        <button className="btn" disabled={busy || !ready}>{t("registry.grant")}</button>
        <button type="button" className="btn danger" disabled={busy || !ready} onClick={() => void run(false)}>{t("registry.revoke")}</button>
      </div>
    </form>
  );
}
