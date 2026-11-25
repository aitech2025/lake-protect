/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, fmtDate, fmtDateTime } from "../api";
import { isAdmin, useAuth } from "../auth";
import { AuthImage, useAsync, usePageTitle } from "../components/Bits";
import { notifyCountChanged } from "../components/Layout";
import { MapView, type Pin } from "../components/MapView";
import { PageState, TableRegion } from "../components/PageState";
import { baseFor, useDataset } from "../dataset";
import { DemoTag, useDemoOnScreen } from "../demo";

/** Citizen reports on the desk (CONTEXT.md 17.8; DECISIONS.md D-062). */
type Row = {
  id: number; ref: string; channel: string; language: string; what: string; description: string | null; lon: number | null; lat: number | null;
  location_text: string | null; photos: number; asset_id: number | null; asset_name: string | null; asset_name_te: string | null; district: string | null;
  mandal: string | null; zone: string | null; alert_id: number | null; alert_code: string | null; alert_state: string | null; duplicate_of: number | null;
  duplicate_of_ref: string | null; duplicates: number; status: string; closed_reason: string | null; false_report: boolean; flags: string[];
  updates: boolean; phone_masked: string | null; has_name: boolean; source_ref: string | null; is_demo: boolean; created_at: string;
};
const STATUS_COLOUR: Record<string, string> = { RECEIVED: "#b5651d", CHECKING: "#1f6fa8", CLOSED: "#75848b" };
const MANUAL_REASONS = ["no_change_seen", "authorised", "passed_on", "not_enough"];
const DEPTS = ["revenue", "municipal", "irrigation", "hydraa", "forest", "endowments", "waqf"];

function placeLabel(r: Row, t: (k: string, o?: any) => string, lang: string): string {
  if (r.asset_name) return `${lang === "te" && r.asset_name_te ? r.asset_name_te : r.asset_name}, ${t(`reports.zone.${r.zone ?? "inside"}`)}`;
  if (r.lon === null) return t("reports.no_place");
  return t("reports.zone.outside");
}

export function Reports() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const { dataset } = useDataset();
  const nav = useNavigate();
  const [filter, setFilter] = useState<"open" | "all" | "CLOSED">("open");
  const [intake, setIntake] = useState(false);
  const { data, error, status, loading, reload } = useAsync(
    () => api<{ items: Row[] }>(`/reports?dataset=${dataset}${filter === "all" ? "" : `&status=${filter}`}`),
    [dataset, filter],
  );
  useDemoOnScreen(dataset === "demo");
  usePageTitle(t("reports.title"));
  const items = data?.items ?? [];
  const pins: Pin[] = useMemo(
    () => items.filter((r) => r.lon !== null).map((r) => ({ id: r.id, lon: r.lon!, lat: r.lat!, colour: STATUS_COLOUR[r.status], label: r.ref, onClick: () => nav(`/reports/${r.id}`) })),
    [items, nav],
  );

  return (
    <div className="page" data-testid="reports">
      <div className="page-head">
        <div>
          <h1>{t("reports.title")}</h1>
          <p className="muted">{t("reports.lede")}</p>
        </div>
        <div className="head-actions">
          <button type="button" className="btn" onClick={() => setIntake((x) => !x)} data-testid="intake-open">{t("reports.enter")}</button>
          {dataset === "demo" && <Link className="btn secondary" to="/reports/whatsapp" data-testid="sim-open">{t("reports.simulator")}</Link>}
          <a className="btn secondary" href={dataset === "demo" ? "/report?demo=1" : "/report"} target="_blank" rel="noreferrer">{t("reports.portal_link")}</a>
        </div>
      </div>
      {intake && <Intake onDone={() => { reload(); }} />}
      <div className="chips" role="group" style={{ marginBottom: "0.75rem" }}>
        {(["open", "all", "CLOSED"] as const).map((f) => (
          <button key={f} type="button" className="chip" aria-pressed={filter === f} onClick={() => setFilter(f)}>{t(`reports.${f === "CLOSED" ? "closed" : f}`)}</button>
        ))}
      </div>
      <PageState loading={loading && !data} error={error} status={status} onRetry={reload} />
      {data && (
        <div className="reports-grid">
          <div className="mapbox" style={{ height: 380 }}>
            <MapView base={baseFor(dataset)} pins={pins} testId="reports-map" />
          </div>
          <TableRegion label={t("reports.title")}>
            <table className="grid" data-testid="reports-table">
              <thead>
                <tr><th>{t("reports.col.ref")}</th><th>{t("reports.col.received")}</th><th>{t("reports.col.what")}</th><th>{t("reports.col.place")}</th><th>{t("reports.col.status")}</th></tr>
              </thead>
              <tbody>
                {items.length === 0 && <tr><td colSpan={5} className="muted">{t("reports.empty")}</td></tr>}
                {items.map((r) => (
                  <tr key={r.id} data-testid={`report-row-${r.ref}`}>
                    <td><Link to={`/reports/${r.id}`}><code>{r.ref}</code></Link> {r.is_demo && <DemoTag />}<div className="small muted">{t(`reports.channel.${r.channel}`)}</div></td>
                    <td>{fmtDateTime(r.created_at, lang)}</td>
                    <td>{t(`reports.what.${r.what}`)}{r.photos > 0 && <span className="small muted"> · {r.photos} 📷</span>}</td>
                    <td>{placeLabel(r, t, lang)}{r.alert_code && <div className="small"><Link to={`/alerts/${r.alert_id}`}>{r.alert_code}</Link></div>}
                      {r.duplicate_of_ref && <div className="small muted">{t("reports.duplicate_of", { ref: r.duplicate_of_ref })}</div>}</td>
                    <td><span className="pill" style={{ background: "#eef1ef", color: STATUS_COLOUR[r.status] }}>{t(`reports.status.${r.status}`)}</span>
                      {r.flags.includes("repeat_false_reports") && <div className="small flag">{t("reports.repeat_false")}</div>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableRegion>
        </div>
      )}
    </div>
  );
}

function Intake({ onDone }: { onDone: () => void }) {
  const { t } = useTranslation();
  const { dataset } = useDataset();
  const [f, setF] = useState({ channel: "helpline_1070", source_ref: "", language: "te", what: "dumping", location_text: "", description: "", caller_phone: "", wants_updates: false });
  const [pin, setPin] = useState<[number, number] | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const set = (k: string) => (e: { target: { value: string } }) => setF((x) => ({ ...x, [k]: e.target.value }));
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setMsg(null);
    const form = new FormData();
    form.append("data", JSON.stringify({ ...f, dataset, lon: pin?.[0] ?? null, lat: pin?.[1] ?? null, source_ref: f.source_ref || null,
      location_text: f.location_text || null, description: f.description || null, caller_phone: f.wants_updates ? f.caller_phone : null }));
    try {
      const out = await api<any>("/reports/intake", { body: form });
      setMsg({ ok: true, text: t("reports.intake_done", { ref: out.ref }) });
      setPin(null);
      setF((x) => ({ ...x, source_ref: "", location_text: "", description: "", caller_phone: "", wants_updates: false }));
      onDone();
    } catch (err) {
      setMsg({ ok: false, text: String((err as Error).message) });
    }
  };
  return (
    <form className="panel intake" onSubmit={(e) => void submit(e)} data-testid="intake">
      <h2 className="title-s">{t("reports.intake_title")}</h2>
      <p className="small muted">{t("reports.intake_lede")}</p>
      <div className="intake-grid">
        <div className="intake-fields">
          <label className="field">{t("reports.intake_channel")}
            <select value={f.channel} onChange={set("channel")}>{["helpline_1070", "praja_vani", "walk_in"].map((c) => <option key={c} value={c}>{t(`reports.channel.${c}`)}</option>)}</select>
          </label>
          <label className="field">{t("reports.intake_source_ref")}<input value={f.source_ref} onChange={set("source_ref")} data-testid="intake-source" /></label>
          <label className="field">{t("reports.intake_language")}
            <select value={f.language} onChange={set("language")}><option value="te">తెలుగు</option><option value="en">English</option><option value="ur">اردو</option></select>
          </label>
          <label className="field">{t("reports.col.what")}
            <select value={f.what} onChange={set("what")} data-testid="intake-what">{["dumping", "construction", "fencing", "clearing", "other"].map((w) => <option key={w} value={w}>{t(`reports.what.${w}`)}</option>)}</select>
          </label>
          <label className="field">{t("reports.intake_location_text")}<input value={f.location_text} onChange={set("location_text")} /></label>
          <label className="field">{t("reports.intake_description")}<textarea rows={2} value={f.description} onChange={set("description")} data-testid="intake-description" /></label>
          <label className="check"><input type="checkbox" checked={f.wants_updates} onChange={(e) => setF((x) => ({ ...x, wants_updates: e.target.checked }))} /> {t("reports.intake_wants")}</label>
          {f.wants_updates && <label className="field">{t("reports.intake_phone")}<input type="tel" value={f.caller_phone} onChange={set("caller_phone")} /></label>}
        </div>
        <div>
          <p className="small muted">{t("reports.intake_place")}</p>
          <div className="mapbox" style={{ height: 300 }}>
            <MapView base={baseFor(dataset)} draft={pin ? [pin] : []} onMapClick={(p) => setPin(p)} testId="intake-map" />
          </div>
          {pin && <p className="small" data-testid="intake-pin">{pin[1].toFixed(5)}, {pin[0].toFixed(5)}</p>}
        </div>
      </div>
      {msg && <p className={`banner ${msg.ok ? "info" : "stop"}`} role="status" data-testid="intake-message">{msg.text}</p>}
      <div className="person-foot"><button type="submit" className="btn" data-testid="intake-submit">{t("reports.intake_submit")}</button></div>
    </form>
  );
}

export function ReportDetail() {
  const { id } = useParams();
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const { user } = useAuth();
  const admin = isAdmin(user);
  const { data: r, error, status, loading, reload } = useAsync(() => api<any>(`/reports/${id}`), [id]);
  useDemoOnScreen(!!r?.is_demo);
  usePageTitle(r ? `${t("reports.title")}: ${r.ref}` : t("reports.title"));
  const [outcome, setOutcome] = useState<"visible" | "not_visible">("visible");
  const [checkNote, setCheckNote] = useState("");
  const [reason, setReason] = useState("no_change_seen");
  const [dept, setDept] = useState("revenue");
  const [closeNote, setCloseNote] = useState("");
  const [falseReport, setFalseReport] = useState(false);
  const [assetId, setAssetId] = useState("");
  const [alertId, setAlertId] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const dataset = r ? (r.is_demo ? "demo" : "real") : null;
  const assets = useAsync(() => (admin && dataset ? api<any>(`/assets?dataset=${dataset}`) : Promise.resolve(null)), [admin, dataset]);
  const alerts = useAsync(() => (admin && dataset ? api<any>(`/alerts?dataset=${dataset}`) : Promise.resolve(null)), [admin, dataset]);
  useEffect(() => setMsg(null), [id]);

  const act = async (path: string, json: unknown) => {
    setMsg(null);
    try {
      await api(`/reports/${id}/${path}`, { json });
      setCheckNote("");
      setCloseNote("");
      reload();
      notifyCountChanged();
    } catch (e) {
      setMsg(String((e as Error).message));
    }
  };

  if (!r) return <div className="page"><PageState loading={loading} error={error} status={status} onRetry={reload} /></div>;
  const open = r.status !== "CLOSED";
  const leader = !r.duplicate_of;
  const noteOf = (n: any) => (lang === "te" ? n.te : n.en);

  return (
    <div className="page" data-testid="report-detail">
      <p className="small"><Link to="/reports">← {t("reports.back")}</Link></p>
      <div className="page-head">
        <div>
          <h1><code>{r.ref}</code> {r.is_demo && <DemoTag />}</h1>
          <p className="muted">{t(`reports.what.${r.what}`)} · {t(`reports.channel.${r.channel}`)} · {fmtDateTime(r.created_at, lang)}</p>
        </div>
        <span className="pill" style={{ fontSize: "1rem", color: STATUS_COLOUR[r.status], background: "#eef1ef" }} data-testid="report-status">{t(`reports.status.${r.status}`)}</span>
      </div>
      <div className="report-grid">
        <div>
          <section className="panel">
            <dl className="facts">
              <dt>{t("reports.col.place")}</dt>
              <dd>{placeLabel(r, t, lang)}{r.asset_id && <> · <Link to={`/assets?asset=${r.asset_id}`}>{t("reports.open_location")}</Link></>}
                {r.location_text && <div className="small muted">{r.location_text}</div>}</dd>
              {r.alert_code && <><dt>{t("reports.link_incident")}</dt><dd><Link to={`/alerts/${r.alert_id}`}>{t("reports.open_incident", { code: r.alert_code })}</Link></dd></>}
              {r.source_ref && <><dt>{t("reports.intake_source_ref")}</dt><dd>{r.source_ref}</dd></>}
            </dl>
            {r.duplicate_of_ref && <p className="note"><Link to={`/reports/${r.duplicate_of}`}>{t("reports.duplicate_of", { ref: r.duplicate_of_ref })}</Link></p>}
            {r.duplicates > 0 && <p className="note">{t("reports.duplicates", { n: r.duplicates })}: {r.duplicate_list.map((d: any) => d.ref).join(", ")}</p>}
            <p className="small">{r.updates ? t("reports.updates_yes", { to: r.phone_masked }) : t("reports.updates_no")}</p>
            {r.flags.includes("repeat_false_reports") && <p className="banner warn">{t("reports.repeat_false")}</p>}
            {r.description && (<><h3 className="small" style={{ marginTop: "0.75rem" }}>{t("reports.description")}</h3><blockquote className="citizen-words">{r.description}</blockquote></>)}
          </section>
          <section className="section">
            <h2 className="title-s">{t("reports.photos")}</h2>
            {r.photo_list.length === 0 ? <p className="muted">{t("reports.no_photos")}</p> : (
              <div className="report-photos">{r.photo_list.map((p: any) => <AuthImage key={p.n} path={`/reports/${r.id}/photos/${p.n}`} alt={`${r.ref} ${p.n}`} className="report-photo" />)}</div>
            )}
          </section>
          <section className="section">
            <h2 className="title-s">{t("reports.history")}</h2>
            <ol className="report-history" data-testid="report-history">
              {r.events.map((ev: any) => (
                <li key={ev.id} data-kind={ev.kind}>
                  <span className="small muted">{fmtDateTime(ev.at, lang)}{ev.actor ? ` · ${ev.actor}` : ""} · {t(`reports.status.${ev.status}`)}</span>
                  <span><b>{t("reports.citizen_sees")}:</b> {noteOf(ev.note)}</span>
                  {ev.internal_note && <span className="small"><b>{t("reports.internal")}:</b> {ev.internal_note}</span>}
                </li>
              ))}
            </ol>
          </section>
          <section className="section">
            <h2 className="title-s">{t("reports.messages")}</h2>
            {r.messages.length === 0 ? <p className="muted small">{t("reports.no_messages")}</p> : (
              <TableRegion label={t("reports.messages")}>
                <table className="grid small" data-testid="report-messages">
                  <tbody>
                    {r.messages.map((m: any) => (
                      <tr key={m.id}><td>{fmtDateTime(m.at, lang)}</td><td>{m.channel} {m.direction === "in" ? "←" : "→"} {m.to_masked}</td>
                        <td><span className={`delivery ${m.status}`}>{m.status}</span></td><td>{m.detail ?? ""}</td></tr>
                    ))}
                  </tbody>
                </table>
              </TableRegion>
            )}
          </section>
        </div>
        <aside>
          {r.lon !== null && (
            <div className="mapbox" style={{ height: 260, marginBottom: "1rem" }}>
              <MapView base={r.is_demo ? "demo" : "s2"} draft={[[r.lon, r.lat]]} fit={[r.lon - 0.004, r.lat - 0.003, r.lon + 0.004, r.lat + 0.003]} />
            </div>
          )}
          {msg && <p className="banner stop" role="alert">{msg}</p>}
          {open && leader && (
            <form className="panel" onSubmit={(e) => { e.preventDefault(); void act("check", { outcome, note: checkNote }); }} data-testid="check-form">
              <h2 className="title-s">{t("reports.check_title")}</h2>
              <label className="check"><input type="radio" checked={outcome === "visible"} onChange={() => setOutcome("visible")} /> {t("reports.check_visible")}</label>
              <label className="check"><input type="radio" checked={outcome === "not_visible"} onChange={() => setOutcome("not_visible")} data-testid="check-not-visible" /> {t("reports.check_not_visible")}</label>
              <label className="field">{t("reports.note")}<textarea rows={2} value={checkNote} onChange={(e) => setCheckNote(e.target.value)} data-testid="check-note" /></label>
              <button type="submit" className="btn" disabled={!checkNote.trim()} data-testid="check-submit">{t("reports.save_check")}</button>
            </form>
          )}
          {open && leader && admin && (
            <form className="panel" onSubmit={(e) => { e.preventDefault(); void act("link", alertId ? { alert_id: Number(alertId) } : { asset_id: Number(assetId) }); }} data-testid="link-form">
              <h2 className="title-s">{t("reports.link_title")}</h2>
              <label className="field">{t("reports.link_location")}
                <select value={assetId} onChange={(e) => { setAssetId(e.target.value); setAlertId(""); }} data-testid="link-asset">
                  <option value="">{t("reports.choose")}</option>
                  {(assets.data?.features ?? []).filter((f: any) => f.properties.monitored).map((f: any) => <option key={f.id} value={f.id}>{f.properties.name}</option>)}
                </select>
              </label>
              <label className="field">{t("reports.link_incident")}
                <select value={alertId} onChange={(e) => { setAlertId(e.target.value); setAssetId(""); }}>
                  <option value="">{t("reports.choose")}</option>
                  {(alerts.data?.items ?? []).filter((a: any) => ["OPEN", "UNDER_REVIEW", "CONFIRMED"].includes(a.state)).map((a: any) => <option key={a.id} value={a.id}>{a.code} · {a.asset_name}</option>)}
                </select>
              </label>
              <p className="small muted">{t("reports.add_location")}</p>
              <button type="submit" className="btn secondary" disabled={!assetId && !alertId} data-testid="link-submit">{t("reports.link")}</button>
            </form>
          )}
          {open && leader && admin && (
            <form className="panel" onSubmit={(e) => { e.preventDefault(); void act("close", { reason, note: closeNote, department: reason === "passed_on" ? dept : null, false_report: falseReport }); }} data-testid="close-form">
              <h2 className="title-s">{t("reports.close_title")}</h2>
              <label className="field">{t("reports.reason_label")}
                <select value={reason} onChange={(e) => setReason(e.target.value)} data-testid="close-reason">
                  {MANUAL_REASONS.map((x) => <option key={x} value={x}>{t(`reports.reason.${x}`)}</option>)}
                </select>
              </label>
              {reason === "passed_on" && (
                <label className="field">{t("reports.department")}
                  <select value={dept} onChange={(e) => setDept(e.target.value)} data-testid="close-dept">{DEPTS.map((d) => <option key={d} value={d}>{t(`reports.dept.${d}`)}</option>)}</select>
                </label>
              )}
              <label className="field">{t("reports.note")}<textarea rows={2} value={closeNote} onChange={(e) => setCloseNote(e.target.value)} data-testid="close-note" /></label>
              <label className="check"><input type="checkbox" checked={falseReport} onChange={(e) => setFalseReport(e.target.checked)} /> {t("reports.false_report")}</label>
              <button type="submit" className="btn danger" disabled={!closeNote.trim()} data-testid="close-submit">{t("reports.close")}</button>
            </form>
          )}
          {!open && r.closed_reason && <p className="note">{t(`reports.reason.${r.closed_reason}`)} · {fmtDate(r.updated_at, lang)}</p>}
        </aside>
      </div>
    </div>
  );
}

/** Demo only: the WhatsApp conversation a citizen has, with a fictional number (D-062). */
export function WhatsAppSim() {
  const { t } = useTranslation();
  const { dataset, setDataset } = useDataset();
  const { data, reload } = useAsync(() => api<any>("/reports/whatsapp-simulator"), []);
  const [chat, setChat] = useState<any>(null);
  const [textIn, setTextIn] = useState("");
  const [showMap, setShowMap] = useState(false);
  const [busy, setBusy] = useState(false);
  const thread = useRef<HTMLOListElement>(null);
  useDemoOnScreen(true);
  usePageTitle(t("reports.sim_title"));
  useEffect(() => {
    if (dataset !== "demo") setDataset("demo");
  }, [dataset, setDataset]);
  useEffect(() => setChat(data), [data]);
  useEffect(() => {
    if (thread.current) thread.current.scrollTop = thread.current.scrollHeight;
  }, [chat]);

  const send = async (body: any) => {
    setBusy(true);
    try {
      setChat(await api<any>("/reports/whatsapp-simulator", { json: body }));
    } finally {
      setBusy(false);
    }
  };
  const sendPhoto = async (file: File | undefined) => {
    if (!file) return;
    const b64 = await new Promise<string>((ok) => {
      const fr = new FileReader();
      fr.onload = () => ok(String(fr.result).split(",")[1] ?? "");
      fr.readAsDataURL(file);
    });
    await send({ type: "image", photo_b64: b64 });
  };

  return (
    <div className="page" data-testid="wa-sim">
      <p className="small"><Link to="/reports">← {t("reports.back")}</Link></p>
      <h1>{t("reports.sim_title")}</h1>
      <p className="muted">{t("reports.sim_lede", { number: chat?.number ?? "" })}</p>
      <div className="wa-wrap">
        <div className="wa-phone">
          <ol className="wa-thread" data-testid="wa-thread" ref={thread} aria-live="polite">
            {(chat?.messages ?? []).map((m: any) => (
              <li key={m.id} className={`wa-msg ${m.direction}`} data-direction={m.direction}>
                <span className="wa-text">{m.text}</span>
                {m.direction === "out" && m.status !== "received" && <span className="wa-meta">{m.status === "held" ? t("reports.sim_held") : m.status}</span>}
              </li>
            ))}
          </ol>
          <form className="wa-input" onSubmit={(e) => { e.preventDefault(); if (textIn.trim()) { void send({ type: "text", text: textIn }); setTextIn(""); } }}>
            <input value={textIn} onChange={(e) => setTextIn(e.target.value)} placeholder={t("reports.sim_type")} aria-label={t("reports.sim_type")} data-testid="wa-text" disabled={busy} />
            <button type="submit" className="btn" disabled={busy} data-testid="wa-send">{t("reports.sim_send")}</button>
          </form>
          <div className="wa-tools">
            <button type="button" className="btn secondary" onClick={() => setShowMap((x) => !x)} data-testid="wa-location">{t("reports.sim_location")}</button>
            <label className="btn secondary portal-file">{t("reports.sim_photo")}
              <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => { void sendPhoto(e.target.files?.[0]); e.target.value = ""; }} data-testid="wa-photo" />
            </label>
            <button type="button" className="btn quiet" onClick={() => reload()}>↻</button>
          </div>
        </div>
        {showMap && (
          <div className="mapbox" style={{ height: 420, flex: 1 }}>
            <MapView base="demo" onMapClick={(p) => { setShowMap(false); void send({ type: "location", longitude: p[0], latitude: p[1] }); }} testId="wa-map" />
          </div>
        )}
      </div>
    </div>
  );
}
