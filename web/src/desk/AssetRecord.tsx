/* eslint-disable @typescript-eslint/no-explicit-any */
import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { API_BASE, api, authHeaders, fmtDate, fmtDateTime } from "../api";
import { isAdmin, isCasework, useAuth } from "../auth";
import { AuthImage, StatePill, useAsync } from "../components/Bits";
import { TableRegion } from "../components/PageState";

const DOC_TYPES = ["notification", "survey_map", "land_record", "government_order", "court_order", "recovery_order", "other"] as const;

/**
 * The asset week by week (D-057): whether it was seen clearly, that week's image, and what
 * changed, each change linked to its incident. "No change seen" only where there was a clear look.
 */
export function WeeklyRecord({ assetId }: { assetId: number }) {
  const { t, i18n } = useTranslation();
  const { data } = useAsync(() => api<{ items: any[] }>(`/assets/${assetId}/weeks?limit=260`), [assetId]);
  const [showArchive, setShowArchive] = useState(false);
  const { active, archive } = useMemo(() => {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - 60);
    const items = data?.items ?? [];
    return { active: items.filter((w) => new Date(w.as_of) >= cutoff), archive: items.filter((w) => new Date(w.as_of) < cutoff) };
  }, [data]);
  if (!data) return null;
  return (
    <section className="section" data-testid="weekly-record">
      <h2>{t("weeks.title")}</h2>
      <p className="muted small" style={{ marginBottom: "0.6rem" }}>{t("weeks.lede")}</p>
      {data.items.length === 0 && <p className="muted">{t("weeks.none")}</p>}
      <ol className="week-strip">
        {active.map((w) => (
          <li key={w.screen_id} className={`week ${w.changed ? "changed" : ""} ${w.status}`} data-testid={`week-${w.week}`} data-status={w.status}>
            <div className="week-head">
              <b>{t("weeks.week", { week: w.week.split("-W")[1], year: w.week.split("-W")[0] })}</b>
              <span className={w.changed ? "flag" : w.status === "no_candidate" ? "ok" : "flag-overdue"}>{t(`weeks.status.${w.status}`)}</span>
            </div>
            {w.has_image ? (
              <AuthImage frame path={`/assets/${assetId}/weeks/${w.screen_id}/image`} alt={t("weeks.image_alt", { week: w.week })} />
            ) : (
              <div className="week-noimage">{t("weeks.no_image")}</div>
            )}
            <span className="small muted">{w.image_date ? t("weeks.look", { date: fmtDate(w.image_date, i18n.language) }) : t("weeks.as_of", { date: fmtDate(w.as_of, i18n.language) })}</span>
            {w.changes.map((c: any) => (
              <span key={c.candidate_id} className="week-change">
                <b className="change-type">{t(`change.${c.change_type}`)}</b>
                <span className="small">{t("weeks.area", { area: Math.round(c.area_sq_m).toLocaleString("en-IN") })}{c.continues ? `, ${t("weeks.continues")}` : ""}</span>
                {c.alert_id && (
                  <Link to={`/alerts/${c.alert_id}`} className="small">
                    {c.alert_code} {c.alert_state && <StatePill state={c.alert_state} />}
                  </Link>
                )}
              </span>
            ))}
          </li>
        ))}
      </ol>
      {archive.length > 0 && <details className="week-archive" open={showArchive} onToggle={(e) => setShowArchive((e.currentTarget as HTMLDetailsElement).open)}>
        <summary>{t("weeks.archive", { count: archive.length })}</summary>
        <ol className="week-strip archived-weeks">
          {archive.map((w) => (
            <li key={w.screen_id} className={`week ${w.changed ? "changed" : ""} ${w.status}`} data-testid={`week-${w.week}`} data-status={w.status}>
              <div className="week-head"><b>{t("weeks.week", { week: w.week.split("-W")[1], year: w.week.split("-W")[0] })}</b><span>{t(`weeks.status.${w.status}`)}</span></div>
              {w.has_image ? <AuthImage frame path={`/assets/${assetId}/weeks/${w.screen_id}/image`} alt={t("weeks.image_alt", { week: w.week })} /> : <div className="week-noimage">{t("weeks.no_image")}</div>}
              <span className="small muted">{w.image_date ? t("weeks.look", { date: fmtDate(w.image_date, i18n.language) }) : t("weeks.as_of", { date: fmtDate(w.as_of, i18n.language) })}</span>
            </li>
          ))}
        </ol>
      </details>}
    </section>
  );
}

async function openFile(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/documents/${id}/file`, { headers: authHeaders() });
  if (!res.ok) throw new Error(String(res.status));
  const url = URL.createObjectURL(await res.blob());
  window.open(url, "_blank", "noopener");
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

/** Legal documents tagged to the asset (D-057). The admin adds them; everyone reads them. */
export function Documents({ assetId }: { assetId: number }) {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const { data, reload } = useAsync(() => api<{ items: any[] }>(`/assets/${assetId}/documents`), [assetId]);
  if (!data) return null;
  return (
    <section className="section" data-testid="documents">
      <h2>{t("docs.title")}</h2>
      {data.items.length === 0 ? (
        <p className="muted">{t("docs.none")}</p>
      ) : (
        <TableRegion label={t("docs.title")}>
          <table className="grid">
            <thead><tr><th>{t("docs.col.type")}</th><th>{t("docs.col.title")}</th><th>{t("docs.col.reference")}</th><th>{t("docs.col.issued")}</th><th>{t("docs.col.file")}</th></tr></thead>
            <tbody>
              {data.items.map((d) => (
                <tr key={d.id} className={d.superseded ? "superseded" : undefined} data-testid={`doc-${d.doc_type}`}>
                  <td>{t(`docs.type.${d.doc_type}`)}</td>
                  <td>{d.title}{d.superseded && <div className="small muted">{t("docs.superseded")}</div>}{d.issued_by && <div className="small muted">{d.issued_by}</div>}</td>
                  <td>{d.reference ?? ""}{d.source_url && <div className="small"><a href={d.source_url} target="_blank" rel="noreferrer">{t("docs.link")}</a></div>}</td>
                  <td>{fmtDate(d.issued_on, i18n.language)}</td>
                  <td>
                    {d.has_file ? (
                      <button className="btn quiet" onClick={() => void openFile(d.id)}>{d.file_name ?? t("docs.open")}</button>
                    ) : (
                      <span className="small muted">{t("docs.no_file")}</span>
                    )}
                    {d.sha256 && <div className="small muted obs-id">SHA-256 {d.sha256.slice(0, 12)}…</div>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableRegion>
      )}
      {isAdmin(user) && <AddDocument assetId={assetId} onDone={reload} />}
    </section>
  );
}

/** Append-only field visit history and evidence for Asset 360. */
export function Inspections({ assetId }: { assetId: number }) {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [outcome, setOutcome] = useState("confirmed");
  const [alertId, setAlertId] = useState("");
  const [notes, setNotes] = useState("");
  const [position, setPosition] = useState<[number, number] | null>(null);
  const [photos, setPhotos] = useState<FileList | null>(null);
  const { data, reload } = useAsync(() => api<{ items: any[] }>(`/assets/${assetId}/inspections`), [assetId]);
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setSaving(true); setMessage(null);
    const body = new FormData();
    body.append("outcome", outcome); body.append("notes", notes); body.append("observed_at", new Date().toISOString());
    if (alertId) body.append("alert_id", alertId);
    if (position) { body.append("lat", String(position[0])); body.append("lon", String(position[1])); }
    Array.from(photos ?? []).slice(0, 5).forEach((file) => body.append("photos", file));
    try {
      await api(`/assets/${assetId}/inspections`, { method: "POST", body });
      setMessage(t("inspection.saved")); setNotes(""); setPhotos(null); setAlertId(""); setPosition(null); setOpen(false); reload();
    } catch (err) { setMessage((err as Error).message); }
    finally { setSaving(false); }
  };
  const capture = () => navigator.geolocation?.getCurrentPosition((p) => setPosition([p.coords.latitude, p.coords.longitude]), () => setMessage(t("inspection.gps_error")), { enableHighAccuracy: true, timeout: 10000 });
  return (
    <section className="section panel" data-testid="asset-inspections">
      <div className="person-head"><div><h2 className="title-s">{t("inspection.title")}</h2><p className="small muted">{t("inspection.lede")}</p></div>
        {!open && isCasework(user) && <button type="button" className="btn secondary" onClick={() => setOpen(true)}>{t("inspection.add")}</button>}
      </div>
      {message && <p className="banner info" role="status">{message}</p>}
      {open && <form className="action inspection-form" onSubmit={(e) => void submit(e)}>
        <label className="field">{t("field.outcome")}<select value={outcome} onChange={(e) => setOutcome(e.target.value)}>{["confirmed", "false_alarm", "cannot_access"].map((v) => <option key={v} value={v}>{t(`field.outcome_${v}`)}</option>)}</select></label>
        <label className="field">{t("inspection.incident")}<input type="number" min="1" value={alertId} onChange={(e) => setAlertId(e.target.value)} placeholder={t("inspection.incident_optional")} /></label>
        <label className="field">{t("field.notes")}<textarea required minLength={3} maxLength={5000} rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} /></label>
        <div className="inspection-gps"><button type="button" className="btn quiet" onClick={capture}>{t("field.get_gps")}</button><span className="small muted">{position ? `${position[0].toFixed(5)}, ${position[1].toFixed(5)}` : t("inspection.gps_optional")}</span></div>
        <label className="field">{t("inspection.photos")}<input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" multiple onChange={(e) => setPhotos(e.target.files)} /></label>
        <div className="person-foot"><button className="btn" type="submit" disabled={saving || notes.trim().length < 3}>{saving ? t("inspection.saving") : t("inspection.save")}</button><button className="btn secondary" type="button" onClick={() => setOpen(false)}>{t("action.cancel")}</button></div>
      </form>}
      {!data?.items.length ? <p className="muted">{t("inspection.empty")}</p> : <ol className="inspection-list">{data.items.map((v) => <li key={v.id}>
        <div className="person-head"><b>{t(`field.outcome_${v.outcome}`)}</b><span className="small muted">{fmtDateTime(v.observed_at, i18n.language)} · {v.inspector}</span></div>
        {v.alert_code && <Link to={`/alerts/${v.alert_id}`}>{v.alert_code}</Link>}<p>{v.notes}</p>
        {v.lat != null && <span className="small muted">{v.lat.toFixed(5)}, {v.lon.toFixed(5)}</span>}
        {!!v.photos && <div className="report-photos">{Array.from({ length: v.photos }, (_, i) => <AuthImage key={i} path={`/assets/${assetId}/inspections/${v.id}/photos/${i + 1}`} alt={`${t("inspection.photo_alt")} ${i + 1}`} className="report-photo" />)}</div>}
      </li>)}</ol>}
    </section>
  );
}

function AddDocument({ assetId, onDone }: { assetId: number; onDone: () => void }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [docType, setDocType] = useState<string>("notification");
  const [title, setTitle] = useState("");
  const [reference, setReference] = useState("");
  const [issued, setIssued] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  if (!open) return <button className="btn secondary" style={{ marginTop: "0.75rem" }} onClick={() => setOpen(true)} data-testid="doc-add">{t("docs.add")}</button>;
  const submit = async () => {
    setError(null);
    const form = new FormData();
    form.append("doc_type", docType);
    form.append("title", title);
    if (reference) form.append("reference", reference);
    if (issued) form.append("issued_on", issued);
    if (file) form.append("file", file);
    try {
      await api(`/assets/${assetId}/documents`, { body: form, method: "POST" });
      setOpen(false);
      setTitle("");
      setReference("");
      setIssued("");
      setFile(null);
      onDone();
    } catch (e) {
      setError((e as Error).message);
    }
  };
  return (
    <form className="action doc-form" onSubmit={(e) => { e.preventDefault(); void submit(); }} data-testid="doc-form">
      <h3 className="title-xs">{t("docs.add")}</h3>
      <label className="field">{t("docs.col.type")}
        <select value={docType} onChange={(e) => setDocType(e.target.value)}>{DOC_TYPES.map((d) => <option key={d} value={d}>{t(`docs.type.${d}`)}</option>)}</select>
      </label>
      <label className="field">{t("docs.col.title")}<input value={title} onChange={(e) => setTitle(e.target.value)} data-testid="doc-title" /></label>
      <label className="field">{t("docs.col.reference")}<input value={reference} onChange={(e) => setReference(e.target.value)} /></label>
      <label className="field">{t("docs.col.issued")}<input type="date" value={issued} onChange={(e) => setIssued(e.target.value)} /></label>
      <label className="field">{t("docs.file_hint")}<input type="file" accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></label>
      {error && <p className="error" role="alert">{error}</p>}
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button className="btn" type="submit" disabled={!title.trim() || (!file && !reference.trim())}>{t("docs.save")}</button>
        <button className="btn secondary" type="button" onClick={() => setOpen(false)}>{t("action.cancel")}</button>
      </div>
    </form>
  );
}
