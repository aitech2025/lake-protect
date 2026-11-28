/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { AnimatePresence, motion } from "motion/react";
import { Camera, CheckCircle2, CornerUpLeft, LocateFixed, MapPin, Send, UserRoundCheck } from "lucide-react";
import { api, API_BASE, authHeaders, fmtDateTime } from "../api";
import { AuthImage, useAsync } from "../components/Bits";
import { notifyCountChanged } from "../components/Layout";

/**
 * The incident's casework (DECISIONS.md D-067): the steps the server offers this person, each with
 * its own form. The district officer reviews, sends a field officer and recommends; the field
 * officer reports from the place; the senior official approves, returns and closes.
 */
const DEPARTMENTS = ["revenue", "municipal", "irrigation", "hydraa", "forest", "endowments", "waqf"];
const OUTCOMES = ["confirmed", "false_alarm", "cannot_access"] as const;

type Step = { action: string; to?: string; label: string; approve?: boolean; direct?: boolean; already_reviewed?: boolean };

/** The words for a step, from what it is and where the incident stands. */
export function stepKey(s: Step, state: string): string {
  if (s.action === "assign") return state === "FIELD_VISIT" ? "case.reassign" : "case.assign";
  if (s.action === "field_report") return "case.report";
  if (s.action === "recommend") return "case.recommend";
  if (s.action !== "transition") return `case.${s.action}`;
  if (s.to === "UNDER_REVIEW") return state === "OPEN" ? "case.start" : state === "FIELD_VISIT" ? "case.withdraw" : "case.return_recommendation";
  if (s.to === "FIELD_VISIT") return "case.return_report";
  if (s.to === "CLOSED") return "case.close";
  const verb = s.approve ? "approve" : "decide";
  return `case.${verb}_${s.to === "CONFIRMED" ? "confirm" : "dismiss"}`;
}

function useSubmit(onDone: (msg: string) => void) {
  const { t } = useTranslation();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (path: string, init: { json?: unknown; body?: FormData }, doneKey = "action.done") => {
    setError(null);
    setBusy(true);
    try {
      if (init.body) {
        const res = await fetch(API_BASE + path, { method: "POST", headers: authHeaders(), body: init.body });
        if (!res.ok) {
          let detail = res.statusText;
          try { const d = await res.json(); detail = typeof d.detail === "string" ? d.detail : JSON.stringify(d.detail); } catch { /* keep status text */ }
          throw new Error(detail);
        }
      } else {
        await api(path, { json: init.json ?? {} });
      }
      notifyCountChanged();
      onDone(t(doneKey));
      return true;
    } catch (e) {
      setError((e as Error).message);
      return false;
    } finally {
      setBusy(false);
    }
  };
  return { error, busy, submit };
}

function StepForm({ title, help, children, testId, onCancel }: { title: string; help?: string; children: ReactNode; testId: string; onCancel: () => void }) {
  const { t } = useTranslation();
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => heading.current?.focus(), []);
  return (
    <motion.div className="action" data-testid={testId} initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.18 }}>
      <div className="step-form-head">
        <h3 className="title-xs" tabIndex={-1} ref={heading}>{title}</h3>
        <button type="button" className="btn quiet small" onClick={onCancel}>{t("action.cancel")}</button>
      </div>
      {help && <p className="why">{help}</p>}
      {children}
    </motion.div>
  );
}

/** A plain step with a note: start, withdraw, return, approve, decide, close. */
function TransitionForm({ alert, step, onDone, onCancel }: { alert: any; step: Step; onDone: (m: string) => void; onCancel: () => void }) {
  const { t } = useTranslation();
  const [note, setNote] = useState("");
  const [dept, setDept] = useState("");
  const [falseReport, setFalseReport] = useState(false);
  const { error, busy, submit } = useSubmit(onDone);
  const key = stepKey(step, alert.state);
  const citizenDismiss = step.direct && step.to === "DISMISSED" && alert.origin === "citizen";
  const send = (e: FormEvent) => {
    e.preventDefault();
    const json: Record<string, unknown> = { to: step.to, note };
    if (citizenDismiss) Object.assign(json, { citizen_department: dept || null, citizen_false_report: falseReport });
    void submit(`/alerts/${alert.id}/transitions`, { json });
  };
  const rec = alert.recommendation;
  return (
    <StepForm title={t(key)} help={t(`${key}_help`, { defaultValue: "" }) || undefined} testId={`form-${step.to}`} onCancel={onCancel}>
      {step.approve && rec && (
        <div className="rec-summary">
          <b>{t(`case.rec.${rec.recommendation}`)}</b>
          <span className="small muted">{t("case.rec_by", { name: rec.by, date: fmtDateTime(rec.at) })}</span>
          <p>{rec.note}</p>
        </div>
      )}
      <form onSubmit={send} className="step-form">
        <label className="field">{t("action.note")}<textarea rows={3} value={note} onChange={(e) => setNote(e.target.value)} data-testid="input-note" /></label>
        {citizenDismiss && <CitizenDismissFields dept={dept} setDept={setDept} falseReport={falseReport} setFalseReport={setFalseReport} />}
        {error && <p className="error" role="alert">{error}</p>}
        <div className="form-actions">
          <button type="submit" className={`btn ${step.to === "DISMISSED" || key.includes("return") ? "danger" : ""}`} disabled={busy || !note.trim()} data-testid="submit-action">
            {t(key)}
          </button>
        </div>
      </form>
    </StepForm>
  );
}

function CitizenDismissFields({ dept, setDept, falseReport, setFalseReport }: { dept: string; setDept: (v: string) => void; falseReport: boolean; setFalseReport: (v: boolean) => void }) {
  const { t } = useTranslation();
  return (
    <>
      <label className="field">{t("citizen_incident.department")}
        <select value={dept} onChange={(e) => setDept(e.target.value)} data-testid="input-department">
          <option value="">{t("citizen_incident.no_department")}</option>
          {DEPARTMENTS.map((d) => <option key={d} value={d}>{t(`reports.dept.${d}`)}</option>)}
        </select>
      </label>
      <label className="check"><input type="checkbox" checked={falseReport} onChange={(e) => setFalseReport(e.target.checked)} /> {t("reports.false_report")}</label>
      <p className="small muted">{t("citizen_incident.told")}</p>
    </>
  );
}

function AssignForm({ alert, onDone, onCancel }: { alert: any; onDone: (m: string) => void; onCancel: () => void }) {
  const { t } = useTranslation();
  const officers = useAsync(() => api<{ items: { id: number; name: string; areas: string[]; open_visits: number }[] }>(`/alerts/${alert.id}/field-officers`), [alert.id]);
  const [who, setWho] = useState("");
  const [note, setNote] = useState("");
  const { error, busy, submit } = useSubmit(onDone);
  const list = officers.data?.items ?? [];
  const current = alert.assignment?.open ? alert.assignment.field_officer_id : null;
  return (
    <StepForm title={t(current ? "case.reassign" : "case.assign")} help={t("case.assign_help")} testId="form-assign" onCancel={onCancel}>
      <form className="step-form" onSubmit={(e) => { e.preventDefault(); void submit(`/alerts/${alert.id}/assignments`, { json: { field_officer_id: Number(who), note } }, "case.assigned"); }}>
        {officers.data && list.length === 0 && <p className="banner warn">{t("case.no_field_officers")}</p>}
        {list.length > 0 && (
          <fieldset className="choices officer-choices">
            <legend className="sr-only">{t("case.field_officer")}</legend>
            {list.map((o) => (
              <label key={o.id} className="check officer-choice">
                <input type="radio" name="field-officer" value={o.id} checked={who === String(o.id)} disabled={o.id === current} onChange={() => setWho(String(o.id))} data-testid={`assign-officer-${o.id}`} />
                <span><b>{o.name}</b><small className="muted">{o.areas.join(", ")} · {t("case.open_visits", { count: o.open_visits })}</small></span>
              </label>
            ))}
          </fieldset>
        )}
        <label className="field">{t("case.assign_note")}<textarea rows={3} value={note} onChange={(e) => setNote(e.target.value)} placeholder={t("case.assign_note_hint")} data-testid="assign-note" /></label>
        {error && <p className="error" role="alert">{error}</p>}
        <div className="form-actions"><button type="submit" className="btn" disabled={busy || !who || !note.trim()} data-testid="assign-submit"><UserRoundCheck aria-hidden="true" />{t("case.assign_submit")}</button></div>
      </form>
    </StepForm>
  );
}

function localNow(): string {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

function FieldReportForm({ alert, onDone, onCancel }: { alert: any; onDone: (m: string) => void; onCancel: () => void }) {
  const { t } = useTranslation();
  const [outcome, setOutcome] = useState<string>("");
  const [findings, setFindings] = useState("");
  const [when, setWhen] = useState(localNow());
  const [gps, setGps] = useState<{ lat: string; lon: string }>({ lat: "", lon: "" });
  const [locating, setLocating] = useState<string | null>(null);
  const [photos, setPhotos] = useState<File[]>([]);
  const { error, busy, submit } = useSubmit(onDone);
  const locate = () => {
    if (!navigator.geolocation) { setLocating(t("case.gps_unavailable")); return; }
    setLocating(t("case.gps_finding"));
    navigator.geolocation.getCurrentPosition(
      (p) => { setGps({ lat: p.coords.latitude.toFixed(6), lon: p.coords.longitude.toFixed(6) }); setLocating(t("case.gps_found", { m: Math.round(p.coords.accuracy) })); },
      () => setLocating(t("case.gps_failed")),
      { enableHighAccuracy: true, timeout: 15000 },
    );
  };
  const send = (e: FormEvent) => {
    e.preventDefault();
    const body = new FormData();
    body.append("outcome", outcome);
    body.append("findings", findings);
    body.append("observed_at", new Date(when).toISOString());
    if (gps.lat && gps.lon) { body.append("lat", gps.lat); body.append("lon", gps.lon); }
    photos.forEach((p) => body.append("photos", p));
    void submit(`/alerts/${alert.id}/field-report`, { body }, "case.reported");
  };
  const gpsPartial = !!gps.lat !== !!gps.lon;
  return (
    <StepForm title={t("case.report")} help={t("case.report_help")} testId="form-field-report" onCancel={onCancel}>
      {alert.assignment?.note && <p className="note"><b>{t("case.assignment_note", { name: alert.assignment.assigned_by })}</b> {alert.assignment.note}</p>}
      <form className="step-form" onSubmit={send}>
        <fieldset className="choices">
          <legend className="field-legend">{t("case.what_found")}</legend>
          {OUTCOMES.map((o) => (
            <label key={o} className="check"><input type="radio" name="outcome" value={o} checked={outcome === o} onChange={() => setOutcome(o)} data-testid={`fr-outcome-${o}`} />{t(`case.outcome.${o}`)}</label>
          ))}
        </fieldset>
        <label className="field">{t("case.findings")}<textarea rows={4} value={findings} onChange={(e) => setFindings(e.target.value)} placeholder={t("case.findings_hint")} data-testid="fr-findings" /></label>
        <label className="field">{t("case.visited_at")}<input type="datetime-local" value={when} max={localNow()} onChange={(e) => setWhen(e.target.value)} data-testid="fr-when" /></label>
        <div className="gps-row">
          <button type="button" className="btn secondary sm" onClick={locate}><LocateFixed aria-hidden="true" />{t("case.use_gps")}</button>
          <label className="field"><span className="sr-only">{t("case.lat")}</span><input inputMode="decimal" placeholder={t("case.lat")} aria-label={t("case.lat")} value={gps.lat} onChange={(e) => setGps({ ...gps, lat: e.target.value })} /></label>
          <label className="field"><span className="sr-only">{t("case.lon")}</span><input inputMode="decimal" placeholder={t("case.lon")} aria-label={t("case.lon")} value={gps.lon} onChange={(e) => setGps({ ...gps, lon: e.target.value })} /></label>
        </div>
        {locating && <p className="small muted" role="status">{locating}</p>}
        <div className="photo-pick">
          <label className="btn secondary sm portal-file">
            <Camera aria-hidden="true" />{t("case.add_photos")}
            <input type="file" accept="image/*" capture="environment" multiple onChange={(e) => setPhotos([...photos, ...Array.from(e.target.files ?? [])].slice(0, 5))} data-testid="fr-photos" />
          </label>
          <span className="small muted">{t("case.photos_count", { count: photos.length })}</span>
          {photos.length > 0 && <button type="button" className="btn quiet small" onClick={() => setPhotos([])}>{t("case.clear_photos")}</button>}
        </div>
        <p className="small muted">{t("case.photos_private")}</p>
        {error && <p className="error" role="alert">{error}</p>}
        <div className="form-actions"><button type="submit" className="btn" disabled={busy || !outcome || findings.trim().length < 3 || gpsPartial} data-testid="fr-submit"><Send aria-hidden="true" />{busy ? t("case.sending") : t("case.report_submit")}</button></div>
      </form>
    </StepForm>
  );
}

function RecommendForm({ alert, onDone, onCancel }: { alert: any; onDone: (m: string) => void; onCancel: () => void }) {
  const { t } = useTranslation();
  const [rec, setRec] = useState<"confirm" | "dismiss" | "">("");
  const [note, setNote] = useState("");
  const [dept, setDept] = useState("");
  const [falseReport, setFalseReport] = useState(false);
  const { error, busy, submit } = useSubmit(onDone);
  const citizen = alert.origin === "citizen" && rec === "dismiss";
  const report = (alert.field_reports ?? []).at(-1);
  return (
    <StepForm title={t("case.recommend")} help={t("case.recommend_help")} testId="form-recommend" onCancel={onCancel}>
      {alert.state === "FIELD_REPORTED" && report && <p className="note"><b>{t("case.based_on", { name: report.field_officer })}</b> {t(`case.outcome.${report.outcome}`)}</p>}
      <form className="step-form" onSubmit={(e) => {
        e.preventDefault();
        void submit(`/alerts/${alert.id}/recommendation`, { json: { recommendation: rec, note, ...(citizen ? { citizen_department: dept || null, citizen_false_report: falseReport } : {}) } }, "case.recommended");
      }}>
        <fieldset className="choices">
          <legend className="field-legend">{t("case.recommendation")}</legend>
          <label className="check"><input type="radio" name="rec" checked={rec === "confirm"} onChange={() => setRec("confirm")} data-testid="rec-confirm" />{t("case.rec.confirm")}</label>
          <label className="check"><input type="radio" name="rec" checked={rec === "dismiss"} onChange={() => setRec("dismiss")} data-testid="rec-dismiss" />{t("case.rec.dismiss")}</label>
        </fieldset>
        <label className="field">{t("action.note")}<textarea rows={3} value={note} onChange={(e) => setNote(e.target.value)} data-testid="rec-note" /></label>
        {citizen && <CitizenDismissFields dept={dept} setDept={setDept} falseReport={falseReport} setFalseReport={setFalseReport} />}
        {error && <p className="error" role="alert">{error}</p>}
        <div className="form-actions"><button type="submit" className="btn" disabled={busy || !rec || !note.trim()} data-testid="rec-submit">{t("case.recommend_submit")}</button></div>
      </form>
    </StepForm>
  );
}

/** The step buttons and the open step's form. `review` is drawn by the caller (it has its own form). */
export function CaseworkSteps({ alert, steps, onDone }: { alert: any; steps: Step[]; onDone: (msg: string) => void }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState<string | null>(null);
  useEffect(() => setOpen(null), [alert.state]);
  const done = (m: string) => { setOpen(null); onDone(m); };
  const items = steps.filter((s) => s.action !== "review" && s.action !== "evidence_pack");
  if (!items.length) return null;
  const id = (s: Step) => `${s.action}:${s.to ?? ""}`;
  const primary = (s: Step) => s.action === "field_report" || s.action === "recommend" || s.approve || (s.action === "transition" && s.to === "CLOSED");
  const current = items.find((s) => id(s) === open);
  return (
    <div className="casework-steps">
      <div className="step-buttons">
        {items.map((s) => {
          const key = stepKey(s, alert.state);
          const danger = key.includes("return") || key.includes("withdraw") || (s.to === "DISMISSED" && !s.approve);
          return (
            <button key={id(s)} type="button" aria-expanded={open === id(s)}
              className={`btn ${primary(s) ? "" : danger ? "danger" : "secondary"}`}
              data-testid={s.action === "transition" ? `action-${s.to}` : `action-${s.action}`}
              onClick={() => setOpen(open === id(s) ? null : id(s))}>
              {s.action === "assign" ? <UserRoundCheck aria-hidden="true" /> : s.action === "field_report" ? <MapPin aria-hidden="true" /> :
                key.includes("return") ? <CornerUpLeft aria-hidden="true" /> : s.approve ? <CheckCircle2 aria-hidden="true" /> : null}
              {t(key)}
            </button>
          );
        })}
      </div>
      <AnimatePresence initial={false}>
        {current && (
          <div key={id(current)}>
            {current.action === "assign" && <AssignForm alert={alert} onDone={done} onCancel={() => setOpen(null)} />}
            {current.action === "field_report" && <FieldReportForm alert={alert} onDone={done} onCancel={() => setOpen(null)} />}
            {current.action === "recommend" && <RecommendForm alert={alert} onDone={done} onCancel={() => setOpen(null)} />}
            {current.action === "transition" && <TransitionForm alert={alert} step={current} onDone={done} onCancel={() => setOpen(null)} />}
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

/** Where the casework stands: the field visit, the field reports with their evidence, the recommendation. */
export function FieldWork({ a }: { a: any }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const reports: any[] = a.field_reports ?? [];
  const rec = a.recommendation;
  if (!a.assignment && !reports.length && !rec) return null;
  return (
    <section className="section panel fieldwork" data-testid="fieldwork" aria-labelledby="fieldwork-title">
      <h2 className="title-s" id="fieldwork-title">{t("case.fieldwork_title")}</h2>
      {a.assignment && (
        <p className="fieldwork-assignment" data-testid="fieldwork-assignment">
          <UserRoundCheck aria-hidden="true" />
          <span>
            {t(a.assignment.open ? "case.assigned_to" : "case.was_assigned_to", { name: a.assignment.field_officer })}
            <small className="muted">{t("case.assigned_by", { name: a.assignment.assigned_by, date: fmtDateTime(a.assignment.at, lang) })}{a.assignments.length > 1 ? ` · ${t("case.assignments", { count: a.assignments.length })}` : ""}</small>
          </span>
        </p>
      )}
      {reports.length > 0 && (
        <ol className="field-reports">
          {reports.slice().reverse().map((r, i) => (
            <li key={r.id} className={i === 0 ? "latest" : ""} data-testid="field-report">
              <div className="field-report-head">
                <span className={`pill ${r.outcome === "confirmed" ? "open" : r.outcome === "false_alarm" ? "ok" : "closed"}`}>{t(`case.outcome.${r.outcome}`)}</span>
                <span className="small muted">{t("case.report_by", { name: r.field_officer, date: fmtDateTime(r.observed_at ?? r.submitted_at, lang) })}</span>
              </div>
              <p className="field-findings">{r.findings}</p>
              <p className="small muted">
                {r.lat != null ? <span className="mono">{Number(r.lat).toFixed(5)}, {Number(r.lon).toFixed(5)}</span> : t("case.no_gps")}
                {" · "}{t("case.photos_count", { count: r.photos })}
              </p>
              {r.photos > 0 && (
                <div className="report-photos">
                  {Array.from({ length: r.photos }, (_, n) => (
                    <AuthImage key={n} path={`/assets/${r.asset_id}/inspections/${r.inspection_id}/photos/${n + 1}`} alt={t("case.photo_alt", { n: n + 1, name: r.field_officer })} className="report-photo" />
                  ))}
                </div>
              )}
            </li>
          ))}
        </ol>
      )}
      {rec && (
        <div className={`rec-summary${rec.pending ? " pending" : ""}`} data-testid="recommendation">
          <b>{t("case.recommended_to", { what: t(`case.rec.${rec.recommendation}`) })}</b>
          <span className="small muted">{t("case.rec_by", { name: rec.by, date: fmtDateTime(rec.at, lang) })}{rec.pending ? ` · ${t("case.awaiting_senior")}` : ""}</span>
          <p>{rec.note}</p>
          {rec.citizen_department && <p className="small">{t("case.rec_department", { dept: t(`reports.dept.${rec.citizen_department}`) })}</p>}
        </div>
      )}
      {!a.district_officer_covers && <p className="small muted">{t("case.no_district_officer")}</p>}
    </section>
  );
}


