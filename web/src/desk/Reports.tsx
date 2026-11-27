/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, fmtDate, fmtDateTime } from "../api";
import { AuthImage, useAsync, usePageTitle } from "../components/Bits";
import { notifyCountChanged } from "../components/Layout";
import { MapView, type Pin } from "../components/MapView";
import { PageState, TableRegion } from "../components/PageState";

/** Citizen reports on the desk (CONTEXT.md 17.8; DECISIONS.md D-062). */
type Row = {
  id: number; ref: string; channel: string; language: string; what: string; description: string | null; lon: number | null; lat: number | null;
  location_text: string | null; photos: number; asset_id: number | null; asset_name: string | null; asset_name_te: string | null; district: string | null;
  mandal: string | null; zone: string | null; alert_id: number | null; alert_code: string | null; alert_state: string | null; duplicate_of: number | null;
  duplicate_of_ref: string | null; duplicates: number; status: string; closed_reason: string | null; false_report: boolean; flags: string[];
  updates: boolean; phone_masked: string | null; has_name: boolean; source_ref: string | null; created_at: string;
};
const STATUS_COLOUR: Record<string, string> = { RECEIVED: "#b5651d", CHECKING: "#1f6fa8", CLOSED: "#75848b" };

function placeLabel(r: Row, t: (k: string, o?: any) => string, lang: string): string {
  if (r.asset_name) return `${lang === "te" && r.asset_name_te ? r.asset_name_te : r.asset_name}, ${t(`reports.zone.${r.zone ?? "inside"}`)}`;
  if (r.lon === null) return t("reports.no_place");
  return t("reports.zone.outside");
}

export function Reports() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const nav = useNavigate();
  const [filter, setFilter] = useState<"open" | "all" | "CLOSED">("open");
  const [intake, setIntake] = useState(false);
  const { data, error, status, loading, reload } = useAsync(
    () => api<{ items: Row[] }>(`/reports${filter === "all" ? "" : `?status=${filter}`}`),
    [filter],
  );
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
          <a className="btn secondary" href="/report" target="_blank" rel="noreferrer">{t("reports.portal_link")}</a>
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
            <MapView pins={pins} testId="reports-map" />
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
                    <td><Link to={`/reports/${r.id}`}><code>{r.ref}</code></Link><div className="small muted">{t(`reports.channel.${r.channel}`)}</div></td>
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
  const [f, setF] = useState({ channel: "helpline_1070", source_ref: "", language: "te", what: "dumping", location_text: "", description: "", caller_phone: "", wants_updates: false });
  const [pin, setPin] = useState<[number, number] | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const set = (k: string) => (e: { target: { value: string } }) => setF((x) => ({ ...x, [k]: e.target.value }));
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setMsg(null);
    const form = new FormData();
    form.append("data", JSON.stringify({ ...f, lon: pin?.[0] ?? null, lat: pin?.[1] ?? null, source_ref: f.source_ref || null,
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
            <select value={f.language} onChange={set("language")}><option value="te">తెలుగు</option><option value="en">English</option></select>
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
            <MapView draft={pin ? [pin] : []} onMapClick={(p) => setPin(p)} testId="intake-map" />
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
  const { data: r, error, status, loading, reload } = useAsync(() => api<any>(`/reports/${id}`), [id]);
  usePageTitle(r ? `${t("reports.title")}: ${r.ref}` : t("reports.title"));
  const [pin, setPin] = useState<[number, number] | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  useEffect(() => {
    setMsg(null);
    setPin(null);
  }, [id]);

  const place = async () => {
    if (!pin) return;
    setMsg(null);
    try {
      await api(`/reports/${id}/place`, { json: { lon: pin[0], lat: pin[1] } });
      reload();
      notifyCountChanged();
    } catch (e) {
      setMsg(String((e as Error).message));
    }
  };

  if (!r) return <div className="page"><PageState loading={loading} error={error} status={status} onRetry={reload} /></div>;
  const noteOf = (n: any) => (lang === "te" ? n.te : n.en);

  return (
    <div className="page" data-testid="report-detail">
      <p className="small"><Link to="/reports">← {t("reports.back")}</Link></p>
      <div className="page-head">
        <div>
          <h1><code>{r.ref}</code></h1>
          <p className="muted">{t(`reports.what.${r.what}`)} · {t(`reports.channel.${r.channel}`)} · {fmtDateTime(r.created_at, lang)}</p>
        </div>
        <span className="pill" style={{ fontSize: "1rem", color: STATUS_COLOUR[r.status], background: "#eef1ef" }} data-testid="report-status">{t(`reports.status.${r.status}`)}</span>
      </div>
      <div className="report-grid">
        <div>
          {r.alert_code && (
            <section className="panel report-incident" data-testid="report-incident">
              <p><Link className="btn" to={`/alerts/${r.alert_id}`} data-testid="open-incident">{t("reports.open_incident", { code: r.alert_code })}</Link></p>
              <p className="small muted">{t("reports.incident_flow")}</p>
            </section>
          )}
          <section className="panel section">
            <dl className="facts">
              <dt>{t("reports.col.place")}</dt>
              <dd>{placeLabel(r, t, lang)}{r.asset_id && <> · <Link to={`/assets/${r.asset_id}`}>{t("reports.open_location")}</Link></>}
                {r.location_text && <div className="small muted">{r.location_text}</div>}</dd>
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
          {r.lon !== null ? (
            <div className="mapbox" style={{ height: 260 }}>
              <MapView draft={[[r.lon, r.lat]]} fit={[r.lon - 0.004, r.lat - 0.003, r.lon + 0.004, r.lat + 0.003]} />
            </div>
          ) : (
            <section className="panel" data-testid="place-form">
              <h2 className="title-s">{t("reports.place_title")}</h2>
              <p className="small muted">{t("reports.place_help")}</p>
              <div className="mapbox" style={{ height: 300 }}>
                <MapView draft={pin ? [pin] : []} onMapClick={(p) => setPin(p)} testId="place-map" />
              </div>
              {pin && <p className="small">{pin[1].toFixed(5)}, {pin[0].toFixed(5)}</p>}
              <button type="button" className="btn" disabled={!pin} onClick={() => void place()} data-testid="place-submit">{t("reports.place")}</button>
            </section>
          )}
          {msg && <p className="banner stop" role="alert">{msg}</p>}
          {r.status === "CLOSED" && r.closed_reason && <p className="note">{t(`reports.reason.${r.closed_reason}`)} · {fmtDate(r.updated_at, lang)}</p>}
        </aside>
      </div>
    </div>
  );
}
