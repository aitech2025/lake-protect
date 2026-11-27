/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { API_BASE, api, authHeaders, fmtDate, fmtDateTime } from "../api";
import { isAdmin, useAuth } from "../auth";
import { AuthImage, BoundarySeal, LineSwatch, StatePill, useAsync, usePageTitle } from "../components/Bits";
import { DatedBracket } from "../components/DatedBracket";
import { MapView } from "../components/MapView";
import { PageState } from "../components/PageState";
import { AckBanner } from "./Inbox";
import { notifyCountChanged } from "../components/Layout";
import { CitizenMain, CitizenSide } from "./CitizenActions";

const OUTCOMES = ["real_change", "not_real", "needs_site_visit"] as const;

async function download(path: string): Promise<void> {
  const res = await fetch(API_BASE + path, { headers: authHeaders() });
  if (!res.ok) throw new Error(String(res.status));
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.target = "_blank";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

/** One plain sentence: what changed, how big, where, and when it was first seen. */
export function ChangeSummary({ a }: { a: any }) {
  const { t, i18n } = useTranslation();
  if (a.origin === "citizen") {
    // A citizen incident: what was reported, when, and what the satellite review shows (D-063).
    return <p className="change-summary" data-testid="change-summary">{i18n.language === "te" && a.summary_te ? a.summary_te : a.summary}</p>;
  }
  const zone = a.zone ? t(a.asset_type && a.asset_type !== "lake" && a.zone === "inside_ftl" ? "incident.where.parcel_inside" : `incident.where.${a.zone}`) : "";
  return (
    <p className="change-summary" data-testid="change-summary">
      {t("incident.summary", {
        change: t(`change.${a.change_type}`),
        area: Math.round(a.area_sq_m).toLocaleString("en-IN"),
        zone,
        date: fmtDate(a.first_changed_at, i18n.language),
      })}
    </p>
  );
}

export function AlertDetail() {
  const { id } = useParams();
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const { user } = useAuth();
  const { data: a, error, status, reload } = useAsync(() => api<any>(`/alerts/${id}`), [id]);
  // A review or a decision acknowledges this person's notification: refresh the side bar's count.
  useEffect(() => {
    if (a) notifyCountChanged();
  }, [a]);

  const boundaries = useMemo(() => ({ type: "FeatureCollection" as const, features: a?.boundary.features ?? [] }), [a]);
  const changes = useMemo(
    () => ({ type: "FeatureCollection" as const, features: a ? [{ type: "Feature" as const, properties: {}, geometry: a.candidate.geometry }] : [] }),
    [a],
  );
  const titleName = a ? (lang === "te" && a.asset.name_te ? a.asset.name_te : a.asset.name) : null;
  usePageTitle(titleName ? `${titleName} · ${t("nav.queue")}` : t("nav.queue"));

  if (error || !a) {
    return (
      <div className="page">
        <p className="crumbs"><Link to="/alerts">{t("detail.back")}</Link></p>
        <PageState loading={!error} error={error} status={status} onRetry={reload} />
      </div>
    );
  }

  const assetName = lang === "te" && a.asset.name_te ? a.asset.name_te : a.asset.name;
  const isParcel = a.asset.type !== "lake"; // every other kind of location has a parcel boundary
  const lc = a.legal_check;
  const cand = a.candidate;
  const obs = cand.observations;

  return (
    <div className="page" data-testid="alert-detail">
      <div className="detail-head">
        <div>
          <p className="crumbs"><Link to="/alerts">{t("detail.back")}</Link> / {a.code}</p>
          <h1 style={{ marginTop: "0.35rem" }}>{assetName}</h1>
          <div className="sub">
            <StatePill state={a.state} />
            {a.resolution && <span data-testid="resolution">{t(`resolution.${a.resolution}`)}</span>}
            <span className="change-type" data-testid="change-type">{t(`change.${cand.change_type}`)}</span>
            <span>{t("queue.acres", { acres: a.area_acres })}</span>
            {cand.stage_estimate && <span>{t(`stage.${cand.stage_estimate}`)}</span>}
          </div>
        </div>
        <BoundarySeal status={a.boundary.status} version={a.boundary.version} />
      </div>
      <p className="banner disclaimer" role="note">{t("statement.imagery")}</p>
      <ChangeSummary a={a} />
      <section className="section panel observation-summary" aria-labelledby="observation-window-title">
        <h2 id="observation-window-title" className="title-s">{t("detail.bracket_title")}</h2>
        <DatedBracket baseline={a.asset.baseline_date} cutoff={a.policy_cutoff_date} lastClear={cand.last_clear_at} firstChanged={cand.first_changed_at} detected={a.created_at} />
      </section>
      <AckBanner notes={a.my_notifications ?? []} isAdminUser={isAdmin(user)} onDone={reload} />
      <Flags a={a} />
      {a.citizen && <CitizenOrigin a={a} />}

      <div className="detail">
        <section className="panel detail-decision" aria-labelledby="next-step-title">
          <h2 id="next-step-title" className="title-s">{t("detail.actions_title")}</h2>
          {a.officer ? <CitizenSide a={a} onDone={reload} /> : <Actions alert={a} onDone={reload} />}
          {a.satellite_review && <SatelliteReviewPanel a={a} />}
        </section>

        <div className="detail-evidence">
          {cand.has_image_pair ? (
            <>
              <div className="pair" data-testid="image-pair">
                <figure>
                  <AuthImage frame path={`/alerts/${a.id}/chips/before`} alt={`${t("detail.before")}, ${fmtDate(a.satellite_review?.before_date ?? cand.last_clear_at, lang)}`} />
                  <figcaption><b>{t("detail.before")}</b><span>{fmtDate(a.satellite_review?.before_date ?? cand.last_clear_at, lang)}</span></figcaption>
                </figure>
                <figure>
                  <AuthImage frame path={`/alerts/${a.id}/chips/after`} alt={`${t("detail.after")}, ${fmtDate(a.satellite_review?.after_date ?? cand.first_changed_at, lang)}`} />
                  <figcaption><b>{t("detail.after")}</b><span>{fmtDate(a.satellite_review?.after_date ?? cand.first_changed_at, lang)}</span></figcaption>
                </figure>
              </div>
              <div className="img-legend">
                <span><LineSwatch colour="#46a0ff" />{isParcel ? t("zone_parcel.inside_ftl") : t("zone.inside_ftl")}</span>
                {!isParcel && <span><LineSwatch colour="#e6463c" dash="4 3" />{t("zone.buffer")}</span>}
                <span><LineSwatch colour="#ffd640" dash="3 3" />{t(`change.${cand.change_type}`)}</span>
                <span>{t("detail.sensor")}: {t(`sensor.${cand.sensor_basis}`)}{cand.optical_confirmation_pending ? `, ${t("sensor.pending")}` : ""}</span>
                {obs[0] && <span>{obs[0].licence_notice}</span>}
              </div>
            </>
          ) : a.satellite_review?.has_images ? (
            <div className="pair single" data-testid="image-latest">
              <figure>
                <AuthImage frame path={`/alerts/${a.id}/chips/after`} alt={`${t("citizen_incident.latest")}, ${fmtDate(a.satellite_review.after_date, lang)}`} />
                <figcaption><b>{t("citizen_incident.latest")}</b><span>{fmtDate(a.satellite_review.after_date, lang)}</span></figcaption>
              </figure>
            </div>
          ) : null}

          {a.officer && <CitizenMain a={a} onDone={reload} />}

          <section className="section">
            <h2 className="title-s">{t("detail.map_title")}</h2>
            <div className="mapbox" style={{ height: 380 }}>
              <MapView boundaries={boundaries} changes={changes} testId="detail-map" />
              <div className="legend">
                <span><LineSwatch colour="#1f6fa8" />{t("boundary.legend_solid")}</span>
                <span><LineSwatch colour="#1f6fa8" dash="6 4" />{t("boundary.legend_dashed")}</span>
                <span><LineSwatch colour="#1f6fa8" dash="1.5 3" />{t("boundary.legend_dotted")}</span>
                <span><LineSwatch colour="#c4402f" dash="5 3" />{t("zone.buffer")}</span>
              </div>
            </div>
          </section>

          <section className="section panel" data-testid="reviews">
            <h2 className="title-s">{t("review.title")}</h2>
            {a.reviews.length === 0 && <p className="muted small" style={{ marginTop: "0.5rem" }}>{t("review.none")}</p>}
            <ul className="review-list">
              {a.reviews.map((r: any) => (
                <li key={r.id} data-outcome={r.outcome}>
                  <b>{t(`review.outcome.${r.outcome}`)}</b>
                  <span className="small muted">{r.reviewer}, {fmtDateTime(r.reviewed_at, lang)}</span>
                  <span>{r.note}</span>
                </li>
              ))}
            </ul>
          </section>

          <CitizenReportsOn alertId={a.id} />

          <p className="statement" data-testid="statement">{t("statement.imagery")}</p>
        </div>

        <aside className="detail-side">
          <EvidencePanel alert={a} onChange={reload} />

          <div className="panel" data-testid="legal-panel">
            <h2 className="title-s">{t("detail.checks_title")}</h2>
            {lc && (
              <dl className="facts" style={{ marginTop: "0.75rem" }}>
                <dt>{t("detail.zone")}</dt>
                <dd>{t(isParcel && lc.zone === "inside_ftl" ? "zone_parcel.inside_ftl" : `zone.${lc.zone}`)}</dd>
                <dt>{t("detail.boundary")}</dt>
                <dd>{t(`boundary.${lc.boundary_status}`)}, {t("boundary.version", { v: lc.boundary_version })}</dd>
                <dt>{t("detail.class")}</dt>
                <dd>{t(`class.${lc.alert_class}`)}</dd>
                <dt>{t("detail.permits")}</dt>
                <dd>{lc.matched_permit_id ? t("detail.matched", { id: lc.matched_permit_id }) : t("detail.none_found")}</dd>
                <dt>{t("detail.works")}</dt>
                <dd>{lc.matched_work_id ? t("detail.matched", { id: lc.matched_work_id }) : t("detail.none_found")}</dd>
                <dt>{t("detail.court")}</dt>
                <dd>{lc.matched_court_case_id || lc.live_court_matter_now ? t("detail.live_court", { id: lc.matched_court_case_id ?? lc.live_court_matter_now }) : t("detail.none_found")}</dd>
                <dt>{t("detail.confidence")}</dt>
                <dd>{Math.round(cand.confidence * 100)}%</dd>
                <dt>{t("incident.documents")}</dt>
                <dd><Link to={`/assets/${a.asset.id}?tab=documents`}>{t("incident.documents_count", { count: a.asset.documents })}</Link></dd>
              </dl>
            )}
            {lc && <p className="small muted" style={{ marginTop: "0.6rem" }}>{t("detail.rule_version", { v: lc.rule_version })}</p>}
          </div>

          <div className="panel" data-testid="imagery-panel">
            <h2 className="title-s">{t("imagery.title")}</h2>
            <ul className="obs-list">
              {obs.map((o: any) => (
                <li key={o.id}>
                  <b>{t(`imagery.sensor.${o.sensor}`, { defaultValue: o.sensor })}</b>, {fmtDate(o.acquired_at, lang)}
                  {o.cloud_pct !== null && o.cloud_pct !== undefined ? `, ${t("imagery.cloud", { pct: Math.round(o.cloud_pct) })}` : ""}
                  <span className="small muted obs-id">{o.scene_id}</span>
                </li>
              ))}
            </ul>
            {cand.flags.length > 0 && (
              <ul className="small flag-list">
                {cand.flags.map((f: string) => <li key={f}>{t(`imagery.flag.${f}`, { defaultValue: f })}</li>)}
              </ul>
            )}
            <p className="small muted" style={{ marginTop: "0.6rem" }}>{t("imagery.rules", { v: cand.rule_version })}</p>
          </div>

          <div className="panel">
            <h2 className="title-s">{t("detail.timeline_title")}</h2>
            <ol className="timeline" style={{ marginTop: "0.75rem" }} data-testid="timeline">
              {a.timeline.slice().reverse().map((e: any) => (
                <li key={e.id}>
                  <b>{timelineText(e, t)}</b>
                  {fmtDateTime(e.at, lang)}{e.actor_role !== "system" ? `, ${t("timeline.by", { name: e.actor })}` : ""}
                  {e.details?.note ? <span className="muted">. {e.details.note}</span> : null}
                </li>
              ))}
            </ol>
          </div>
        </aside>
      </div>
    </div>
  );
}

function Flags({ a }: { a: any }) {
  const { t } = useTranslation();
  const lc = a.legal_check;
  return (
    <div className="flags" data-testid="flags">
      {lc?.auto_close_reason && <p className="banner info">{t(`incident.auto.${lc.verdict}`, { defaultValue: lc.auto_close_reason })}</p>}
      {(a.court_matter || lc?.live_court_matter_now) && <p className="banner stop">{t("incident.court")}</p>}
      {!a.boundary_confirmed && <p className="banner warn">{t("incident.boundary_unconfirmed")}</p>}
      {lc?.permit_conflict && <p className="banner warn">{t("detail.permit_conflict")}</p>}
      {a.related && <p className="banner info">{t("incident.related")} <Link to={`/alerts/${a.related.id}`}>{a.related.code}</Link></p>}
    </div>
  );
}

function timelineText(e: any, t: (k: string, o?: any) => string): string {
  if (e.action === "alert.transition") return t("timeline.alert.transition", { to: t(`state.${e.details?.to}`) });
  if (e.action === "incident.reviewed") return t("timeline.incident.reviewed", { outcome: t(`review.outcome.${e.details?.outcome}`) });
  const key = `timeline.${e.action}`;
  const text = t(key);
  return text === key ? e.action : text;
}

function Actions({ alert, onDone }: { alert: any; onDone: () => void }) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [message, setMessage] = useState<{ text: string; n: number } | null>(null);
  const messageRef = useRef<HTMLParagraphElement>(null);
  const show = (text: string) => setMessage((m) => ({ text, n: (m?.n ?? 0) + 1 }));
  useEffect(() => {
    if (message) messageRef.current?.focus();
  }, [message]);

  const actions: any[] = alert.allowed_actions;
  const review = actions.find((x) => x.action === "review");
  const steps = actions.filter((x) => x.action === "transition");
  const admin = isAdmin(user);
  const open = !["CLOSED"].includes(alert.state);

  return (
    <div className="actions" style={{ marginTop: "0.75rem" }} data-testid="actions">
      {actions.length === 0 && (
        <p className="muted small">{alert.state === "CLOSED" ? t("action.closed") : admin ? t("action.wait_review") : t("action.none")}</p>
      )}
      {review && <ReviewForm alertId={alert.id} already={review.already_reviewed} onDone={(msg) => { show(msg); onDone(); }} />}
      {steps.map((x) => (
        <DecisionForm key={x.to} alertId={alert.id} to={x.to} citizen={alert.citizen_reports > 0} onDone={(msg) => { show(msg); onDone(); }} />
      ))}
      {admin && open && (
        <button className="btn quiet" onClick={() => api(`/alerts/${alert.id}/imagery-request`, { json: {} }).then(() => show(t("detail.imagery_done")))}>
          {t("detail.imagery")}
        </button>
      )}
      {message && <p className="banner info" role="status" tabIndex={-1} ref={messageRef}>{message.text}</p>}
    </div>
  );
}

function ReviewForm({ alertId, already, onDone }: { alertId: number; already: boolean; onDone: (msg: string) => void }) {
  const { t } = useTranslation();
  const [outcome, setOutcome] = useState<string>("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const submit = async () => {
    setError(null);
    try {
      await api(`/alerts/${alertId}/reviews`, { json: { outcome, note } });
      setOutcome("");
      setNote("");
      onDone(t("review.saved"));
    } catch (e) {
      setError((e as Error).message);
    }
  };
  return (
    <form className="action review-form" data-testid="review-form" onSubmit={(e) => { e.preventDefault(); void submit(); }}>
      <h3 className="title-xs">{t("review.form_title")}</h3>
      {already && <p className="why">{t("review.already")}</p>}
      <fieldset className="choices">
        <legend className="sr-only">{t("review.form_title")}</legend>
        {OUTCOMES.map((o) => (
          <label key={o} className="check">
            <input type="radio" name="outcome" value={o} checked={outcome === o} onChange={() => setOutcome(o)} data-testid={`review-${o}`} />
            {t(`review.outcome.${o}`)}
          </label>
        ))}
      </fieldset>
      <label className="field">{t("review.note")}<textarea rows={3} value={note} onChange={(e) => setNote(e.target.value)} data-testid="review-note" /></label>
      {error && <p className="error" role="alert">{error}</p>}
      <button className="btn" type="submit" disabled={!outcome || !note.trim()} data-testid="review-submit">{t("review.submit")}</button>
    </form>
  );
}

const DEPARTMENTS = ["revenue", "municipal", "irrigation", "hydraa", "forest", "endowments", "waqf"];

function DecisionForm({ alertId, to, citizen, onDone }: { alertId: number; to: string; citizen: boolean; onDone: (msg: string) => void }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState("");
  const [department, setDepartment] = useState("");
  const [falseReport, setFalseReport] = useState(false);
  const forCitizen = citizen && to === "DISMISSED";
  const [error, setError] = useState<string | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    if (open) headingRef.current?.focus();
  }, [open]);
  const danger = to === "DISMISSED";
  if (!open) {
    return (
      <button className={`btn ${danger ? "danger" : to === "CLOSED" ? "secondary" : ""}`} onClick={() => setOpen(true)} data-testid={`action-${to}`}>
        {t(`action.${to}`)}
      </button>
    );
  }
  const submit = async () => {
    setError(null);
    try {
      await api(`/alerts/${alertId}/transitions`, {
        json: forCitizen ? { to, note, citizen_department: department || null, citizen_false_report: falseReport } : { to, note },
      });
      setOpen(false);
      setNote("");
      onDone(t("action.done"));
    } catch (e) {
      setError((e as Error).message);
    }
  };
  return (
    <div className="action" data-testid={`form-${to}`}>
      <h3 className="title-xs" tabIndex={-1} ref={headingRef}>{t(`action.${to}`)}</h3>
      <label className="field">{t("action.note")}<textarea rows={3} value={note} onChange={(e) => setNote(e.target.value)} data-testid="input-note" /></label>
      {forCitizen && (
        <>
          <label className="field">{t("citizen_incident.department")}
            <select value={department} onChange={(e) => setDepartment(e.target.value)} data-testid="input-department">
              <option value="">{t("citizen_incident.no_department")}</option>
              {DEPARTMENTS.map((d) => <option key={d} value={d}>{t(`reports.dept.${d}`)}</option>)}
            </select>
          </label>
          <label className="check"><input type="checkbox" checked={falseReport} onChange={(e) => setFalseReport(e.target.checked)} /> {t("reports.false_report")}</label>
          <p className="small muted">{t("citizen_incident.told")}</p>
        </>
      )}
      {error && <p className="error" role="alert">{error}</p>}
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button className={`btn ${danger ? "danger" : ""}`} disabled={!note.trim()} onClick={() => void submit()} data-testid="submit-action">{t("action.submit")}</button>
        <button className="btn secondary" onClick={() => setOpen(false)}>{t("action.cancel")}</button>
      </div>
    </div>
  );
}

function EvidencePanel({ alert, onChange }: { alert: any; onChange: () => void }) {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const packs: any[] = alert.evidence_packs;
  const latest = packs[packs.length - 1];
  const canMake = isAdmin(user) && alert.resolution === "confirmed";
  if (!latest && !canMake) return null;
  const make = async () => {
    setBusy(true);
    setError(null);
    try {
      await api(`/alerts/${alert.id}/evidence-pack`, { method: "POST" });
      onChange();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="panel" data-testid="evidence-panel">
      <h2 className="title-s">{t("pack.title")}</h2>
      <p className="disclaimer" role="note">{t("statement.imagery")}</p>
      {latest ? (
        <>
          <p className="small" style={{ marginTop: "0.5rem" }}>
            {t("pack.version", { v: latest.version })}, {fmtDateTime(latest.generated_at, i18n.language)}
            <span className="obs-id small muted">SHA-256 {latest.manifest_sha256.slice(0, 16)}…</span>
          </p>
          {!latest.counsel_reviewed && <p className="small flag">{t("pack.draft")}</p>}
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginTop: "0.5rem" }}>
            <button className="btn secondary" onClick={() => void download(`/alerts/${alert.id}/evidence-pack/pdf`)} data-testid="pack-pdf">{t("pack.pdf")}</button>
            <button className="btn secondary" onClick={() => void download(`/alerts/${alert.id}/evidence-pack`)} data-testid="pack-zip">{t("pack.zip")}</button>
          </div>
        </>
      ) : (
        <p className="muted small" style={{ marginTop: "0.5rem" }}>{t("pack.none")}</p>
      )}
      {canMake && (
        <button className="btn" style={{ marginTop: "0.6rem" }} disabled={busy} onClick={() => void make()} data-testid="pack-generate">
          {busy ? t("pack.working") : latest ? t("pack.regenerate") : t("pack.generate")}
        </button>
      )}
      {error && <p className="error" role="alert">{error}</p>}
    </div>
  );
}

/** Citizens' reports of this place (D-062): references and what they saw, never who they are. */
function CitizenReportsOn({ alertId }: { alertId: number }) {
  const { t, i18n } = useTranslation();
  const { data } = useAsync(() => api<{ items: any[] }>(`/reports?alert_id=${alertId}`), [alertId]);
  if (!data || data.items.length === 0) return null;
  return (
    <section className="section panel" data-testid="citizen-reports-on">
      <h2 className="title-s">{t("reports.on_incident")} ({data.items.length})</h2>
      <ul className="review-list">
        {data.items.map((r) => (
          <li key={r.id}>
            <Link to={`/reports/${r.id}`}><code>{r.ref}</code></Link>
            <span className="small muted">{t(`reports.channel.${r.channel}`)}, {fmtDateTime(r.created_at, i18n.language)} · {t(`reports.status.${r.status}`)}</span>
            <span>{t(`reports.what.${r.what}`)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** The report that opened a citizen incident (D-063): what the citizen said and where, never who. */
function CitizenOrigin({ a }: { a: any }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const c = a.citizen;
  return (
    <section className="panel citizen-origin" data-testid="citizen-origin">
      <div className="person-head">
        <h2 className="title-s">{t("citizen_incident.title")}</h2>
        <Link to={`/reports/${c.report_id}`} className="small"><code>{c.ref}</code></Link>
      </div>
      <p className="small muted">
        {t(`reports.channel.${c.channel}`)} · {fmtDateTime(c.created_at, lang)} · {t(`reports.what.${c.what}`)}
        {c.source_ref ? ` · ${c.source_ref}` : ""}
      </p>
      {c.description && <blockquote className="citizen-words">{c.description}</blockquote>}
      <ul className="small citizen-facts">
        <li>{t(`citizen_incident.placed.${c.placed_by ?? "pin"}`)}{c.location_text ? `: ${c.location_text}` : ""}</li>
        {c.reported_place && <li>{t("citizen_incident.reported_place")}</li>}
        {c.area_source && <li>{t("citizen_incident.area_source", { source: c.area_source })}</li>}
        {c.survey_numbers.length > 0 && <li>{t("citizen_incident.survey", { list: c.survey_numbers.map((s: any) => `${s.survey_no}${s.sub_division ? "/" + s.sub_division : ""} (${s.village})`).join(", ") })}</li>}
        <li>{c.updates ? t("citizen_incident.updates_yes") : t("citizen_incident.updates_no")}</li>
      </ul>
      {c.photos > 0 && (
        <div className="report-photos">
          {Array.from({ length: c.photos }, (_, i) => <AuthImage key={i} path={`/reports/${c.report_id}/photos/${i + 1}`} alt={`${c.ref} ${i + 1}`} className="report-photo" />)}
        </div>
      )}
    </section>
  );
}

/** What the satellite showed at the reported place (D-063). */
function SatelliteReviewPanel({ a }: { a: any }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const r = a.satellite_review;
  const key = r.status === "done" ? r.result : r.status;
  return (
    <div className={`satellite-review ${key}`} data-testid="satellite-review">
      <h3 className="title-xs">{t("citizen_incident.review_title")}</h3>
      <p data-testid="satellite-review-result"><b>{t(`citizen_incident.review.${key}`)}</b></p>
      {r.result === "change_found" && r.change_area_sq_m && (
        <p className="small">{t("citizen_incident.review_change", { area: Math.round(r.change_area_sq_m).toLocaleString("en-IN"), date: fmtDate(r.first_changed_at, lang), change: t(`change.${r.change_type}`) })}</p>
      )}
      {r.after_date && <p className="small muted">{t("citizen_incident.review_dates", { before: fmtDate(r.before_date, lang) || "-", after: fmtDate(r.after_date, lang) })}</p>}
      <p className="small muted">{t(`citizen_incident.source.${r.source}`)}{r.detail ? ` · ${r.detail}` : ""}</p>
      {r.status === "pending" && <p className="small">{t("citizen_incident.pending_help")}</p>}
      <p className="small">{t("citizen_incident.next")}</p>
    </div>
  );
}
