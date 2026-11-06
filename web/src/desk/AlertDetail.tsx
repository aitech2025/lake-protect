/* eslint-disable @typescript-eslint/no-explicit-any */
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { api, fmtDate, fmtDateTime } from "../api";
import { useAuth } from "../auth";
import { AuthImage, BoundarySeal, LineSwatch, StatePill, useAsync } from "../components/Bits";
import { DatedBracket } from "../components/DatedBracket";
import { MapView } from "../components/MapView";
import { useDemoOnScreen } from "../demo";
import { CaseFilePanel, Checklist } from "./CaseFile";
import { OfficerRecordPanel } from "./OfficerRecord";

type Action = { to: string; label: string; two_person: boolean; signer: string; enabled: boolean; blocked_reason: string | null; needs: string[] };
const REASON_CODES = ["cloud_shadow", "seasonal_water", "transient_object", "crop_cycle", "image_artefact", "other"];

export function AlertDetail() {
  const { id } = useParams();
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const { data: a, error, reload } = useAsync(() => api<any>(`/alerts/${id}`), [id]);
  useDemoOnScreen(Boolean(a?.is_demo));

  const boundaries = useMemo(() => ({ type: "FeatureCollection" as const, features: a?.boundary.features ?? [] }), [a]);
  const changes = useMemo(
    () => ({ type: "FeatureCollection" as const, features: a ? [{ type: "Feature" as const, properties: {}, geometry: a.candidate.geometry }] : [] }),
    [a],
  );

  if (error) return <div className="page"><p className="error">{t("error.load", { msg: error })}</p></div>;
  if (!a) return <div className="page" aria-busy="true" />;

  const assetName = lang === "te" && a.asset.name_te ? a.asset.name_te : a.asset.name;
  const isParcel = a.asset.type === "recovered_parcel";
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
            <span>{t(`change.${cand.change_type}`)}</span>
            <span>{t("queue.acres", { acres: a.area_acres })}</span>
            {cand.stage_estimate && <span>{t(`stage.${cand.stage_estimate}`)}</span>}
            {a.overdue && <span className="flag-overdue">{t("queue.overdue", { date: fmtDate(a.due_at, lang) })}</span>}
            {!a.overdue && a.due_at && <span>{t("queue.due", { date: fmtDate(a.due_at, lang) })}</span>}
            {a.escalation_level > 0 && <span>{t("detail.escalated", { n: a.escalation_level })}</span>}
            {a.owner_name && <span>{t("queue.owner", { name: a.owner_name })}</span>}
          </div>
        </div>
        <BoundarySeal status={a.boundary.status} version={a.boundary.version} />
      </div>

      <div className="detail">
        <div>
          {cand.has_image_pair ? (
            <>
              <div className="pair" data-testid="image-pair">
                <figure>
                  <AuthImage path={`/alerts/${a.id}/chips/before`} alt={`${t("detail.before")} ${cand.last_clear_at ?? ""}`} />
                  <figcaption><b>{t("detail.before")}</b><span>{fmtDate(cand.last_clear_at, lang)}</span></figcaption>
                </figure>
                <figure>
                  <AuthImage path={`/alerts/${a.id}/chips/after`} alt={`${t("detail.after")} ${cand.first_changed_at}`} />
                  <figcaption><b>{t("detail.after")}</b><span>{fmtDate(cand.first_changed_at, lang)}</span></figcaption>
                </figure>
              </div>
              <div className="img-legend">
                <span><LineSwatch colour="#46a0ff" />{isParcel ? t("zone_parcel.inside_ftl") : t("zone.inside_ftl")}</span>
                {!isParcel && <span><LineSwatch colour="#e6463c" dash="4 3" />{t("zone.buffer")}</span>}
                <span><LineSwatch colour="#ffd640" dash="3 3" />{t("detail.type")}</span>
                <span>{t("detail.sensor")}: {t(`sensor.${cand.sensor_basis}`)}{cand.optical_confirmation_pending ? `, ${t("sensor.pending")}` : ""}</span>
                {obs[0] && <span>{obs[0].licence_notice}</span>}
              </div>
            </>
          ) : null}

          <section className="section panel">
            <h3>{t("detail.bracket_title")}</h3>
            <DatedBracket baseline={a.asset.baseline_date} cutoff={a.policy_cutoff_date} lastClear={cand.last_clear_at} firstChanged={cand.first_changed_at} detected={a.created_at} />
          </section>

          <section className="section">
            <h3>{t("detail.map_title")}</h3>
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

          {a.field_checks.length > 0 && (
            <section className="section panel">
              <h3>{t("detail.field_title")}</h3>
              {a.field_checks.map((f: any) => (
                <p key={f.id} className="small" style={{ marginTop: "0.5rem" }}>
                  <b>{f.officer}</b>, {fmtDateTime(f.observed_at, lang)}: {f.outcome === "confirmed" ? t("state.FIELD_CONFIRMED") : f.outcome === "false_alarm" ? t("state.CLOSED_FALSE_ALARM") : t("form.reason")}
                  {f.observed_stage ? `, ${t(`stage.${f.observed_stage}`)}` : ""}. {t("detail.photos", { count: f.photo_count })}.{" "}
                  {f.distance_to_candidate_m !== null && t("detail.distance", { m: Math.round(f.distance_to_candidate_m) })}
                  {f.notes ? ` ${f.notes}` : ""}
                  <span className="photo-row">
                    {Array.from({ length: f.photo_count }, (_, n) => (
                      <AuthImage key={n} path={`/alerts/${a.id}/field-checks/${f.id}/photos/${n + 1}`} alt={`${t("detail.field_title")} ${n + 1}`} className="photo-thumb" />
                    ))}
                  </span>
                </p>
              ))}
            </section>
          )}

          <Checklist alert={a} onChange={reload} />

          <p className="statement" data-testid="statement">{t("statement.imagery")}</p>
        </div>

        <aside>
          <div className="panel">
            <h3>{t("detail.actions_title")}</h3>
            <Actions alert={a} onDone={reload} />
          </div>

          <OfficerRecordPanel alert={a} onChange={reload} />

          <CaseFilePanel alert={a} onChange={reload} />

          <div className="panel" data-testid="legal-panel">
            <h3>{t("detail.checks_title")}</h3>
            {lc?.permit_conflict && <p className="banner warn" style={{ marginTop: "0.6rem" }}>{t("detail.permit_conflict")}</p>}
            {lc?.live_court_matter_now && <p className="banner stop" style={{ marginTop: "0.6rem" }}>{t("detail.live_court", { id: lc.live_court_matter_now })}</p>}
            {lc && (
              <dl className="facts" style={{ marginTop: "0.75rem" }}>
                <dt>{t("detail.zone")}</dt>
                <dd>{t(isParcel && lc.zone === "inside_ftl" ? "zone_parcel.inside_ftl" : `zone.${lc.zone}`)}</dd>
                <dt>{t("detail.boundary")}</dt>
                <dd>{t(`boundary.${lc.boundary_status}`)}, {t("boundary.version", { v: lc.boundary_version })}</dd>
                <dt>{t("detail.mode")}</dt>
                <dd>{t(`mode.${a.asset.mode}`)}</dd>
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
              </dl>
            )}
            {lc && <p className="small muted" style={{ marginTop: "0.6rem" }}>{t("detail.rule_version", { v: lc.rule_version })}</p>}
          </div>

          <div className="panel">
            <h3>{t("detail.timeline_title")}</h3>
            <ol className="timeline" style={{ marginTop: "0.75rem" }} data-testid="timeline">
              {a.timeline.slice().reverse().map((e: any) => (
                <li key={e.id} className={e.action === "timer.missed" ? "miss" : undefined}>
                  <b>{timelineText(e, t)}</b>
                  {fmtDateTime(e.at, lang)}{e.actor_role !== "system" ? `, ${t("timeline.by", { name: e.actor })}` : ""}
                  {e.details?.reason ? <span className="muted">. {e.details.reason}</span> : null}
                </li>
              ))}
            </ol>
          </div>
        </aside>
      </div>
    </div>
  );
}

function timelineText(e: any, t: (k: string, o?: any) => string): string {
  if (e.action === "alert.transition") {
    if (e.details?.reopened) return t("timeline.reopened");
    return t("timeline.alert.transition", { to: t(`state.${e.details?.to}`) });
  }
  if (e.action === "timer.missed") return t("timeline.timer.missed", { notify: t(`notify.${e.details?.notify}`) });
  const key = `timeline.${e.action}`;
  const text = t(key);
  return text === key ? e.action : text;
}

function Actions({ alert, onDone }: { alert: any; onDone: () => void }) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const actions: Action[] = alert.allowed_actions;
  const [message, setMessage] = useState<string | null>(null);
  const canRequestImagery = user && ["analyst", "nodal_officer"].includes(user.role) && !alert.state.startsWith("CLOSED");

  return (
    <div className="actions" style={{ marginTop: "0.75rem" }} data-testid="actions">
      {alert.pending_closures.map((p: any) => (
        <p key={p.id} className="banner info">{t("detail.pending_closure", { name: p.requested_by, reason: p.reason })}</p>
      ))}
      {actions.length === 0 && <p className="muted small">{t("action.none")}</p>}
      {actions
        .filter((x) => !x.needs.some((n) => n.startsWith("field_check")))
        .map((x) => (
          <ActionForm key={x.to + x.signer} alertId={alert.id} action={x} onDone={(msg) => { setMessage(msg); onDone(); }} />
        ))}
      {canRequestImagery && (
        <button className="btn secondary" onClick={() => api(`/alerts/${alert.id}/imagery-request`, { json: { provider: "commercial_archive" } }).then(() => setMessage(t("detail.imagery_done")))}>
          {t("detail.imagery")}
        </button>
      )}
      {message && <p className="banner info" role="status">{message}</p>}
    </div>
  );
}

function ActionForm({ alertId, action, onDone }: { alertId: number; action: Action; onDone: (msg: string) => void }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [code, setCode] = useState("");
  const [reviewed, setReviewed] = useState(false);
  const [owner, setOwner] = useState("");
  const [due, setDue] = useState("");
  const [caseRef, setCaseRef] = useState("");
  const [gapReason, setGapReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { data: officers } = useAsync(
    () => (action.needs.includes("field_owner") ? api<any[]>("/users?role=field_officer") : Promise.resolve([])),
    [action.needs.join()],
  );
  const needs = new Set(action.needs);
  const second = action.signer === "second";

  if (!action.enabled) {
    return (
      <div className="action">
        <button className="btn secondary" disabled>{t(`action.${action.to}`)}</button>
        <p className="why">{action.blocked_reason}</p>
      </div>
    );
  }

  const submit = async () => {
    setError(null);
    const data: Record<string, unknown> = {};
    if (needs.has("reason_code") && !second) data.reason_code = code;
    if (needs.has("image_pair_reviewed")) data.image_pair_reviewed = reviewed;
    if (needs.has("field_owner")) {
      data.owner_user_id = Number(owner);
      if (due) data.due_at = new Date(due + "T12:00:00Z").toISOString();
    }
    if (needs.has("case_status_ref")) data.case_status_ref = caseRef;
    if (needs.has("gap_reason")) data.gap_reason = gapReason;
    try {
      const out = await api<any>(`/alerts/${alertId}/transitions`, { json: { to: action.to, reason: reason || null, data } });
      onDone(out.status === "awaiting_second_signature" ? t("action.awaiting") : t("action.done"));
      setOpen(false);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const danger = action.to.startsWith("CLOSED");
  if (!open) {
    return (
      <button className={`btn ${danger ? "danger" : ""}`} onClick={() => setOpen(true)} data-testid={`action-${action.to}`}>
        {t(`action.${action.to}`)}
      </button>
    );
  }
  return (
    <div className="action" data-testid={`form-${action.to}`}>
      <b>{t(`action.${action.to}`)}</b>
      {action.two_person && <p className="why">{second ? t("action.second_signature") : t("action.first_signature")}</p>}
      {needs.has("image_pair_reviewed") && (
        <label className="check"><input type="checkbox" checked={reviewed} onChange={(e) => setReviewed(e.target.checked)} data-testid="input-reviewed" />{t("form.image_pair_reviewed")}</label>
      )}
      {needs.has("reason_code") && !second && (
        <label className="field">{t("form.reason_code")}
          <select value={code} onChange={(e) => setCode(e.target.value)} data-testid="input-code">
            <option value="">{t("form.choose")}</option>
            {REASON_CODES.map((c) => <option key={c} value={c}>{t(`form.codes.${c}`)}</option>)}
          </select>
        </label>
      )}
      {needs.has("field_owner") && (
        <>
          <label className="field">{t("form.owner")}
            <select value={owner} onChange={(e) => setOwner(e.target.value)} data-testid="input-owner">
              <option value="">{t("form.choose")}</option>
              {(officers ?? []).map((o: any) => <option key={o.id} value={o.id}>{o.name}</option>)}
            </select>
          </label>
          <label className="field">{t("form.due")}<input type="date" value={due} onChange={(e) => setDue(e.target.value)} /></label>
        </>
      )}
      {needs.has("case_status_ref") && <label className="field">{t("form.case_status_ref")}<input value={caseRef} onChange={(e) => setCaseRef(e.target.value)} /></label>}
      {needs.has("gap_reason") && <label className="field">{t("form.gap_reason")}<textarea rows={2} value={gapReason} onChange={(e) => setGapReason(e.target.value)} /></label>}
      {(needs.has("reason") || second) && (
        <label className="field">{t("form.reason")}<textarea rows={2} value={reason} onChange={(e) => setReason(e.target.value)} data-testid="input-reason" /></label>
      )}
      {error && <p className="error" role="alert">{error}</p>}
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button className={`btn ${danger ? "danger" : ""}`} onClick={() => void submit()} data-testid="submit-action">{t("action.submit")}</button>
        <button className="btn secondary" onClick={() => setOpen(false)}>{t("action.cancel")}</button>
      </div>
    </div>
  );
}
