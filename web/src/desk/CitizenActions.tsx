/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, type FormEvent, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { api, fmtDate, fmtDateTime } from "../api";
import { isAdmin, useAuth } from "../auth";
import { AuthImage, useAsync } from "../components/Bits";
import { notifyCountChanged } from "../components/Layout";

/**
 * What officials and the admin do on an incident a citizen reported (DECISIONS.md D-064):
 * acknowledge, notes, satellite looks to compare, sharper images, legal records and documents,
 * approve or decline, close, and the weekly watch. The server checks every step.
 */
const DEPARTMENTS = ["revenue", "municipal", "irrigation", "hydraa", "forest", "endowments", "waqf"];
const DOC_TYPES = ["notification", "survey_map", "land_record", "government_order", "court_order", "recovery_order", "other"];

function useAct(onDone: () => void) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const run = async (path: string, init: { json?: unknown; body?: FormData }, after?: () => void) => {
    setError(null);
    setBusy(true);
    try {
      await api(path, init.body ? { body: init.body } : { json: init.json ?? {} });
      after?.();
      onDone();
      notifyCountChanged();
      return true;
    } catch (e) {
      setError(String((e as Error).message));
      return false;
    } finally {
      setBusy(false);
    }
  };
  return { error, busy, run };
}

function Block({ title, children, testId }: { title: string; children: ReactNode; testId?: string }) {
  return (
    <div className="officer-block" data-testid={testId}>
      <h3 className="title-xs">{title}</h3>
      {children}
    </div>
  );
}

/** The side panel: acknowledge, decide, close, sharper images and the weekly watch. */
export function CitizenSide({ a, onDone }: { a: any; onDone: () => void }) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const o = a.officer;
  const { error, busy, run } = useAct(onDone);
  const [ackNote, setAckNote] = useState("");
  const [mode, setMode] = useState<"approve" | "decline" | "close" | null>(null);
  const [note, setNote] = useState("");
  const [dept, setDept] = useState("");
  const [falseReport, setFalseReport] = useState(false);
  const sources = useAsync(() => api<{ items: any[] }>("/satellites?purpose=sharper&active=true"), []);
  const providers: any[] = sources.data?.items ?? [];
  const [chosen, setProvider] = useState("");
  const provider = chosen || providers[0]?.key || "";
  const [imgNote, setImgNote] = useState("");
  const [placeName, setPlaceName] = useState("");
  const [reason, setReason] = useState("");
  const closed = a.state === "CLOSED";

  const decide = (e: FormEvent) => {
    e.preventDefault();
    if (!mode) return;
    const json = mode === "decline" ? { decision: mode, note, citizen_department: dept || null, citizen_false_report: falseReport } : { decision: mode, note };
    void run(`/alerts/${a.id}/decision`, { json }, () => { setMode(null); setNote(""); setDept(""); setFalseReport(false); });
  };

  return (
    <div className="officer-side" data-testid="officer-side">
      <Block title={t("act.ack_title")} testId="officer-ack">
        {o.acknowledged_by.length > 0 && <p className="small">{t("act.ack_by", { names: o.acknowledged_by.join(", ") })}</p>}
        {o.acknowledged_by_me ? <p className="small ok">{t("act.ack_done")}</p> : closed ? null : (
          <>
            <textarea rows={2} value={ackNote} onChange={(e) => setAckNote(e.target.value)} placeholder={t("act.ack_note")} aria-label={t("act.ack_note")} data-testid="ack-note" />
            <button type="button" className="btn" disabled={busy} onClick={() => void run(`/alerts/${a.id}/acknowledge`, { json: { note: ackNote || null } }, () => setAckNote(""))} data-testid="ack-submit">
              {t("act.ack")}
            </button>
          </>
        )}
      </Block>

      {(o.can_decide || o.can_close) && (
        <Block title={t("act.decide_title")} testId="officer-decide">
          <div className="officer-buttons">
            {o.can_decide && <button type="button" className="btn" onClick={() => setMode("approve")} data-testid="decide-approve">{t("act.approve")}</button>}
            {o.can_decide && <button type="button" className="btn danger" onClick={() => setMode("decline")} data-testid="decide-decline">{t("act.decline")}</button>}
            {o.can_close && <button type="button" className="btn secondary" onClick={() => setMode("close")} data-testid="decide-close">{t("act.close")}</button>}
          </div>
          {mode && (
            <form onSubmit={decide} className="officer-form" data-testid={`decide-form-${mode}`}>
              <p className="small">{t(`act.means.${mode}`)}</p>
              <label className="field">{t("act.note_required")}<textarea rows={3} value={note} onChange={(e) => setNote(e.target.value)} data-testid="decide-note" /></label>
              {mode === "decline" && (
                <>
                  <label className="field">{t("citizen_incident.department")}
                    <select value={dept} onChange={(e) => setDept(e.target.value)} data-testid="decide-department">
                      <option value="">{t("citizen_incident.no_department")}</option>
                      {DEPARTMENTS.map((d) => <option key={d} value={d}>{t(`reports.dept.${d}`)}</option>)}
                    </select>
                  </label>
                  <label className="check"><input type="checkbox" checked={falseReport} onChange={(e) => setFalseReport(e.target.checked)} /> {t("reports.false_report")}</label>
                </>
              )}
              <p className="small muted">{t("citizen_incident.told")}</p>
              <div className="officer-buttons">
                <button type="submit" className={`btn ${mode === "decline" ? "danger" : ""}`} disabled={busy || !note.trim()} data-testid="decide-submit">{t(`act.${mode}`)}</button>
                <button type="button" className="btn secondary" onClick={() => setMode(null)}>{t("action.cancel")}</button>
              </div>
            </form>
          )}
        </Block>
      )}

      <Block title={t("act.sharper_title")} testId="officer-sharper">
        {!closed && <>
        <p className="small muted">{t("act.sharper_help")}</p>
        <select value={provider} onChange={(e) => setProvider(e.target.value)} aria-label={t("act.provider")} data-testid="sharper-provider">
          {providers.map((p) => (
            <option key={p.key} value={p.key}>{p.name}{p.price_usd_per_sq_km !== null ? ` · US$ ${p.price_usd_per_sq_km}/sq km` : ` · ${t("sat.price_on_request")}`}</option>
          ))}
        </select>
        <input value={imgNote} onChange={(e) => setImgNote(e.target.value)} placeholder={t("act.why_sharper")} aria-label={t("act.why_sharper")} data-testid="sharper-note" />
        <button type="button" className="btn secondary" disabled={busy || !provider} onClick={() => void run(`/alerts/${a.id}/imagery-request`, { json: { provider, note: imgNote || null } }, () => setImgNote(""))} data-testid="sharper-submit">
          {t("act.sharper_request")}
        </button>
        </>}
        {a.imagery_requests.length > 0 && (
          <ul className="officer-list" data-testid="sharper-list">
            {a.imagery_requests.map((r: any) => (
              <li key={r.id}>
                <span><b className={`delivery ${r.status === "approved" ? "sent" : r.status === "declined" ? "failed" : "queued"}`}>{t(`act.img_status.${r.status}`)}</b> {r.provider_name ?? r.provider}
                  {r.est_cost_usd !== null ? ` · ~US$ ${Math.round(r.est_cost_usd).toLocaleString("en-IN")}` : ""}</span>
                <span className="small muted">{r.requested_by}{r.note ? `: ${r.note}` : ""}{r.decided_by && r.status !== "recorded" ? ` · ${r.decided_by}${r.decision_note ? `: ${r.decision_note}` : ""}` : ""}</span>
                {r.status === "requested" && o.can_approve_imagery && (
                  <span className="officer-buttons">
                    <button type="button" className="btn secondary" onClick={() => void run(`/alerts/${a.id}/imagery-requests/${r.id}/decision`, { json: { approve: true } })} data-testid={`sharper-approve-${r.id}`}>{t("act.approve_img")}</button>
                    <button type="button" className="btn secondary" onClick={() => void run(`/alerts/${a.id}/imagery-requests/${r.id}/decision`, { json: { approve: false } })}>{t("act.decline_img")}</button>
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </Block>

      <Block title={t("act.watch_title")} testId="officer-watch">
        {o.can_watch ? (
          <>
            <p className="small muted">{t("act.watch_help")}</p>
            {a.watch.reported_place && <input value={placeName} onChange={(e) => setPlaceName(e.target.value)} placeholder={t("act.watch_name")} aria-label={t("act.watch_name")} data-testid="watch-name" />}
            <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder={t("act.watch_reason")} aria-label={t("act.watch_reason")} data-testid="watch-reason-input" />
            <button type="button" className="btn secondary" disabled={busy || !reason.trim()} onClick={() => void run(`/alerts/${a.id}/watch`, { json: { reason, name: placeName || null } }, () => setReason(""))} data-testid="watch-submit">
              {t("act.watch_add")}
            </button>
          </>
        ) : <p className="small ok" data-testid="watch-on">{t("act.watch_on", { name: a.watch.name })}</p>}
      </Block>
      {error && <p className="banner stop" role="alert">{error}</p>}
      {isAdmin(user) && <p className="small muted">{t("act.admin_told")}</p>}
    </div>
  );
}

/** The main column: notes, satellite looks to compare, legal records and documents. */
export function CitizenMain({ a, onDone }: { a: any; onDone: () => void }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const { error, busy, run } = useAct(onDone);
  const [note, setNote] = useState("");
  const [lookDate, setLookDate] = useState("");
  const [picked, setPicked] = useState<number[]>([]);
  const [doc, setDoc] = useState({ doc_type: "government_order", title: "", reference: "", issued_on: "" });
  const [file, setFile] = useState<File | null>(null);
  const looks: any[] = a.looks ?? [];
  const today = new Date().toISOString().slice(0, 10);
  const lookLabel = (x: any) => (x.kind === "automatic" ? t("act.look_auto") : x.look_date ? t("act.look_on", { date: fmtDate(x.look_date, lang) }) : t("act.look_latest"));
  const pick = (id: number) => setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id].slice(-2)));
  const compare = looks.filter((x) => picked.includes(x.id) && x.has_after);
  const records = a.legal_records?.records;

  const addDoc = (e: FormEvent) => {
    e.preventDefault();
    const body = new FormData();
    Object.entries(doc).forEach(([k, v]) => v && body.append(k, v));
    if (file) body.append("file", file);
    void run(`/alerts/${a.id}/documents`, { body }, () => { setDoc({ doc_type: "government_order", title: "", reference: "", issued_on: "" }); setFile(null); });
  };

  return (
    <>
      <section className="section panel" data-testid="officer-looks">
        <h2 className="title-s">{t("act.looks_title")}</h2>
        <p className="small muted">{t("act.looks_help")}</p>
        <div className="officer-row">
          <label className="field">{t("act.look_date")}
            <input type="date" min="2017-01-01" max={today} value={lookDate} onChange={(e) => setLookDate(e.target.value)} data-testid="look-date" />
          </label>
          <button type="button" className="btn secondary" disabled={busy} onClick={() => void run(`/alerts/${a.id}/satellite-looks`, { json: { date: lookDate || null } })} data-testid="look-submit">
            {lookDate ? t("act.look_request_date") : t("act.look_request_latest")}
          </button>
        </div>
        <div className="look-grid" data-testid="look-list">
          {looks.map((x) => (
            <label key={x.id} className={`look-card${picked.includes(x.id) ? " picked" : ""}`}>
              <input type="checkbox" checked={picked.includes(x.id)} onChange={() => pick(x.id)} disabled={!x.has_after} data-testid={`look-pick-${x.id}`} />
              {x.has_after ? <AuthImage path={`/alerts/${a.id}/looks/${x.id}/after`} alt={lookLabel(x)} className="look-thumb" /> : <div className="look-thumb pending" />}
              <b className="small">{lookLabel(x)}</b>
              <span className="small">{x.status === "done" ? t(`citizen_incident.review.${x.result}`) : t(`citizen_incident.review.${x.status}`)}</span>
              {x.after_date && <span className="small muted">{t("act.image_of", { date: fmtDate(x.after_date, lang) })}</span>}
              {x.requested_by && <span className="small muted">{x.requested_by}</span>}
            </label>
          ))}
        </div>
        {compare.length === 2 ? (
          <div className="pair" data-testid="look-compare">
            {compare.map((x) => (
              <figure key={x.id}>
                <AuthImage frame path={`/alerts/${a.id}/looks/${x.id}/after`} alt={lookLabel(x)} />
                <figcaption><b>{lookLabel(x)}</b><span>{fmtDate(x.after_date, lang)}</span></figcaption>
              </figure>
            ))}
          </div>
        ) : looks.length > 1 && <p className="small muted">{t("act.compare_help")}</p>}
      </section>

      <section className="section panel" data-testid="officer-notes">
        <h2 className="title-s">{t("act.notes_title")}</h2>
        <ol className="report-history">
          {(a.notes ?? []).map((n: any) => (
            <li key={n.id} data-kind={n.kind}>
              <span className="small muted">{fmtDateTime(n.at, lang)} · {n.author} · {t(`act.note_kind.${n.kind}`)}</span>
              <span>{n.text}</span>
            </li>
          ))}
        </ol>
        <form className="officer-row" onSubmit={(e) => { e.preventDefault(); void run(`/alerts/${a.id}/notes`, { json: { text: note } }, () => setNote("")); }}>
          <textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} placeholder={t("act.note_placeholder")} aria-label={t("act.note_placeholder")} data-testid="note-text" />
          <button type="submit" className="btn secondary" disabled={busy || !note.trim()} data-testid="note-submit">{t("act.note_add")}</button>
        </form>
        <p className="small muted">{t("act.notes_inside")}</p>
      </section>

      <section className="section panel" data-testid="officer-legal">
        <div className="person-head">
          <h2 className="title-s">{t("act.legal_title")}</h2>
          <button type="button" className="btn secondary" disabled={busy} onClick={() => void run(`/alerts/${a.id}/legal-records`, { json: {} })} data-testid="legal-attach">
            {records ? t("act.legal_refresh") : t("act.legal_attach")}
          </button>
        </div>
        {!records ? <p className="small muted">{t("act.legal_help")}</p> : (
          <div className="legal-snapshot" data-testid="legal-snapshot">
            <p className="small muted">{t("act.legal_as_of", { date: fmtDateTime(a.legal_records.at, lang), by: a.legal_records.by, n: a.legal_records.snapshots })}</p>
            <dl className="facts">
              <dt>{t("act.legal.place")}</dt>
              <dd>{records.place.name}{records.place.survey_numbers.length > 0 ? ` · ${t("act.legal.survey", { list: records.place.survey_numbers.join(", ") })}` : ""}</dd>
              <dt>{t("act.legal.boundary")}</dt>
              <dd>{records.boundary ? `${t(`boundary.${records.boundary.status}`)}, v${records.boundary.version} · ${records.boundary.source}${records.boundary.notification_ref ? ` · ${records.boundary.notification_ref}` : ""}` : "-"}</dd>
              <dt>{t("act.legal.check")}</dt>
              <dd>{records.legal_check ? `${records.legal_check.verdict} · ${records.legal_check.zone}${records.legal_check.flags.length ? ` · ${records.legal_check.flags.join(", ")}` : ""}` : "-"}</dd>
            </dl>
            <LegalList title={t("act.legal.land")} rows={records.land_records} render={(r) => `${r.survey_no}${r.sub_division ? "/" + r.sub_division : ""}, ${r.village}: ${t(`land.${r.land_category}`, { defaultValue: r.land_category })}${r.extent_acres ? `, ${r.extent_acres} ac` : ""}${r.overlap_sq_m ? ` (${Math.round(r.overlap_sq_m).toLocaleString("en-IN")} sq m overlap)` : ""}`} />
            <LegalList title={t("act.legal.documents")} rows={records.documents} render={(d) => `${t(`docs.type.${d.doc_type}`, { defaultValue: d.doc_type })}: ${d.title}${d.reference ? ` (${d.reference})` : ""}${d.issued_on ? `, ${fmtDate(d.issued_on, lang)}` : ""}`} />
            <LegalList title={t("act.legal.courts")} rows={records.court_cases} render={(c) => `${c.court} ${c.case_no}: ${c.status}${c.next_hearing ? `, ${t("act.legal.next", { date: fmtDate(c.next_hearing, lang) })}` : ""}`} />
            <LegalList title={t("act.legal.permits")} rows={records.permits} render={(p) => `${p.kind} ${p.ref} (${p.source}), ${fmtDate(p.valid_from, lang)}${p.valid_to ? ` – ${fmtDate(p.valid_to, lang)}` : ""}`} />
            <LegalList title={t("act.legal.works")} rows={records.authorised_works} render={(w) => `${w.agency}: ${w.description} (${w.ref})`} />
            <p className="small muted">{t("act.legal.not_connected", { list: records.not_connected.join("; ") })}</p>
          </div>
        )}
        <h3 className="title-xs" style={{ marginTop: "0.75rem" }}>{t("act.doc_title")}</h3>
        {(a.documents_attached ?? []).length > 0 && (
          <ul className="officer-list" data-testid="doc-list">
            {a.documents_attached.map((d: any) => <li key={d.id}>{t(`docs.type.${d.doc_type}`, { defaultValue: d.doc_type })}: {d.title}{d.reference ? ` (${d.reference})` : ""} <span className="small muted">{d.added_by}</span></li>)}
          </ul>
        )}
        <form className="officer-doc" onSubmit={addDoc} data-testid="doc-form">
          <select value={doc.doc_type} onChange={(e) => setDoc({ ...doc, doc_type: e.target.value })} aria-label={t("act.doc_type")}>
            {DOC_TYPES.map((d) => <option key={d} value={d}>{t(`docs.type.${d}`, { defaultValue: d })}</option>)}
          </select>
          <input value={doc.title} onChange={(e) => setDoc({ ...doc, title: e.target.value })} placeholder={t("act.doc_name")} aria-label={t("act.doc_name")} data-testid="doc-title" />
          <input value={doc.reference} onChange={(e) => setDoc({ ...doc, reference: e.target.value })} placeholder={t("act.doc_ref")} aria-label={t("act.doc_ref")} data-testid="doc-ref" />
          <input type="date" value={doc.issued_on} onChange={(e) => setDoc({ ...doc, issued_on: e.target.value })} aria-label={t("act.doc_date")} />
          <input type="file" accept="application/pdf,image/*" onChange={(e) => setFile(e.target.files?.[0] ?? null)} aria-label={t("act.doc_file")} />
          <button type="submit" className="btn secondary" disabled={busy || !doc.title.trim() || (!doc.reference.trim() && !file)} data-testid="doc-submit">{t("act.doc_attach")}</button>
        </form>
      </section>
      {error && <p className="banner stop" role="alert">{error}</p>}
    </>
  );
}

function LegalList({ title, rows, render }: { title: string; rows: any[]; render: (r: any) => string }) {
  const { t } = useTranslation();
  return (
    <div className="legal-list">
      <b className="small">{title}</b>
      {rows.length === 0 ? <p className="small muted">{t("act.legal.none")}</p> : <ul className="small">{rows.map((r, i) => <li key={i}>{render(r)}</li>)}</ul>}
    </div>
  );
}
