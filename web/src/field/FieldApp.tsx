/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { fmtDate, fmtDateTime } from "../api";
import { useAuth } from "../auth";
import { MapView } from "../components/MapView";
import { DemoBand, useDemoOnScreen } from "../demo";
import { centroidOf, distanceToPolygonM, offsetM } from "./geo";
import { db, type QueuedCapture } from "./store";
import { isPretendOffline, newUuid, onSyncChange, queueCapture, queued, refreshAlerts, setPretendOffline, sha256Hex, syncNow, type SyncResult } from "./sync";
import "./field.css";

const WARN_M = 50;

function useOnline(): boolean {
  const [online, setOnline] = useState(navigator.onLine && !isPretendOffline());
  useEffect(() => {
    const update = () => setOnline(navigator.onLine && !isPretendOffline());
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    const off = onSyncChange(update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
      off();
    };
  }, []);
  return online;
}

function useQueue(): QueuedCapture[] {
  const [items, setItems] = useState<QueuedCapture[]>([]);
  useEffect(() => {
    const load = () => void queued().then(setItems);
    load();
    return onSyncChange(load);
  }, []);
  return items;
}

export function FieldApp() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const online = useOnline();
  const queue = useQueue();
  const [lastSync, setLastSync] = useState<SyncResult | null>(null);
  const [demoNoSignal, setDemoNoSignal] = useState(isPretendOffline());

  const sync = useCallback(async () => {
    const res = await syncNow();
    setLastSync(res);
    if (!res.offline) await refreshAlerts();
  }, []);

  useEffect(() => {
    if (online) void sync();
    const timer = window.setInterval(() => navigator.onLine && !isPretendOffline() && void sync(), 20_000);
    return () => window.clearInterval(timer);
  }, [online, sync]);

  const toggleDemo = () => {
    setPretendOffline(!demoNoSignal);
    setDemoNoSignal(!demoNoSignal);
  };

  return (
    <div className="field" data-testid="field-app">
      <DemoBand />
      <header className="f-head">
        <div>
          <b>{user?.name}</b>
          <span className={`net ${online ? "on" : "off"}`} data-testid="net-status">{online ? t("field.online") : t("field.offline")}</span>
        </div>
        <div className="f-head-actions">
          <button onClick={() => void i18n.changeLanguage(i18n.language === "te" ? "en" : "te")} data-testid="field-lang">{t("nav.language")}</button>
        </div>
      </header>
      <div className="f-sync">
        {queue.length > 0 ? (
          <span data-testid="queue-count">{t("field.waiting", { count: queue.length })}</span>
        ) : (
          <span data-testid="queue-count">{t("field.all_sent")}</span>
        )}
        <button onClick={() => void sync()} disabled={!online} data-testid="sync-now">{t("field.sync")}</button>
        {user?.is_demo && (
          <label className="demo-switch">
            <input type="checkbox" checked={demoNoSignal} onChange={toggleDemo} data-testid="demo-no-signal" />
            {t("field.demo_no_signal")}
          </label>
        )}
      </div>
      {queue.some((q) => q.status === "failed") && (
        <p className="f-banner stop">{queue.filter((q) => q.status === "failed").map((q) => t("field.failed", { msg: q.error })).join(" ")}</p>
      )}
      {lastSync && lastSync.sent.length > 0 && (
        <p className="f-banner ok" role="status" data-testid="sync-result">
          {lastSync.sent.map((s) => (s.step_refused ? t("field.step_refused", { msg: s.step_refused }) : t("field.sent", { code: s.alert_code, state: t(`state.${s.state}`) }))).join(" ")}
        </p>
      )}
      <Routes>
        <Route index element={<FieldList />} />
        <Route path="alerts/:id" element={<FieldAlert online={online} afterSave={sync} />} />
      </Routes>
    </div>
  );
}

function FieldList() {
  const { t, i18n } = useTranslation();
  const [alerts, setAlerts] = useState<any[] | null>(null);
  const [refreshed, setRefreshed] = useState<string | null>(null);
  useEffect(() => {
    const load = async () => {
      const d = await db();
      const rows = await d.getAll("alerts");
      rows.sort((a: any, b: any) => String(a.due_at).localeCompare(String(b.due_at)));
      setAlerts(rows);
      setRefreshed((await d.get("meta", "last_refresh")) as string | null);
    };
    void load();
    return onSyncChange(() => void load());
  }, []);
  useDemoOnScreen(Boolean(alerts?.some((a) => a.is_demo)));
  const name = (a: any) => (i18n.language === "te" && a.asset_name_te ? a.asset_name_te : a.asset_name);

  return (
    <main className="f-main">
      <h1>{t("field.my_alerts")}</h1>
      {refreshed && <p className="f-muted">{t("field.updated", { time: fmtDateTime(refreshed, i18n.language) })}</p>}
      {alerts && alerts.length === 0 && <p className="f-muted">{t("field.empty")}</p>}
      <ul className="f-list">
        {alerts?.map((a) => (
          <li key={a.id}>
            <Link to={`/field/alerts/${a.id}`} data-testid={`field-alert-${a.code}`}>
              <b>{name(a)}</b>
              <span>{t(`change.${a.change_type}`)}, {t("queue.acres", { acres: a.area_acres })}</span>
              <span className={a.overdue ? "late" : ""}>{a.overdue ? t("queue.overdue", { date: fmtDate(a.due_at, i18n.language) }) : t("queue.due", { date: fmtDate(a.due_at, i18n.language) })}</span>
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}

function ChipImage({ id, which, alt }: { id: number; which: string; alt: string }) {
  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => {
    let url: string | null = null;
    void db().then((d) => d.get("chips", `${id}:${which}`)).then((blob) => {
      if (blob) {
        url = URL.createObjectURL(blob);
        setSrc(url);
      }
    });
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [id, which]);
  return src ? <img src={src} alt={alt} /> : <div className="f-img-missing" aria-label={alt} />;
}

type Fix = { lat: number; lon: number; accuracy: number; simulated: boolean };

function FieldAlert({ online, afterSave }: { online: boolean; afterSave: () => Promise<void> }) {
  const { id } = useParams();
  const { t, i18n } = useTranslation();
  const nav = useNavigate();
  const [a, setA] = useState<any | null>(null);
  const [photos, setPhotos] = useState<File[]>([]);
  const [fix, setFix] = useState<Fix | null>(null);
  const [posMode, setPosMode] = useState<"device" | "site" | "far">("device");
  const [outcome, setOutcome] = useState<"confirmed" | "false_alarm" | "cannot_access" | "">("");
  const [stage, setStage] = useState("");
  const [notes, setNotes] = useState("");
  const [message, setMessage] = useState<{ kind: string; text: string } | null>(null);
  const [gpsError, setGpsError] = useState<string | null>(null);

  useEffect(() => {
    void db().then((d) => d.get("details", Number(id))).then((v) => setA(v ?? null));
  }, [id]);
  useDemoOnScreen(Boolean(a?.is_demo));

  const geom = a?.candidate?.geometry as GeoJSON.Geometry | undefined;
  const centre = useMemo(() => (geom ? centroidOf(geom) : null), [geom]);
  const distance = fix && geom ? Math.round(distanceToPolygonM(fix.lon, fix.lat, geom)) : null;
  const boundaries = useMemo(() => ({ type: "FeatureCollection" as const, features: a?.boundary?.features ?? [] }), [a]);
  const changes = useMemo(() => ({ type: "FeatureCollection" as const, features: geom ? [{ type: "Feature" as const, properties: {}, geometry: geom }] : [] }), [geom]);

  if (!a) return <main className="f-main"><p className="f-muted">{t("field.empty")}</p></main>;
  const name = i18n.language === "te" && a.asset.name_te ? a.asset.name_te : a.asset.name;

  const getPosition = () => {
    setGpsError(null);
    if (posMode !== "device" && centre) {
      const [lon, lat] = posMode === "site" ? offsetM(centre[0], centre[1], 6, -4) : offsetM(centre[0], centre[1], 200, 0);
      setFix({ lon, lat, accuracy: 5, simulated: true });
      return;
    }
    if (!navigator.geolocation) {
      setGpsError(t("field.gps_unavailable"));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (p) => setFix({ lat: p.coords.latitude, lon: p.coords.longitude, accuracy: Math.round(p.coords.accuracy), simulated: false }),
      (err) => setGpsError(err.message || t("field.gps_unavailable")),
      { enableHighAccuracy: true, timeout: 15_000, maximumAge: 0 },
    );
  };

  const save = async () => {
    setMessage(null);
    if (!outcome) return setMessage({ kind: "stop", text: t("field.choose_outcome") });
    if (outcome === "confirmed" && (photos.length === 0 || !fix)) return setMessage({ kind: "stop", text: t("field.need_photo") });
    if (outcome !== "confirmed" && !notes.trim()) return setMessage({ kind: "stop", text: t("field.need_reason") });
    const now = new Date().toISOString();
    const hashes = await Promise.all(photos.map(sha256Hex));
    const note = [notes.trim(), fix?.simulated ? t("field.simulated_note") : ""].filter(Boolean).join(" ");
    const item: QueuedCapture = {
      client_uuid: newUuid(),
      alert_id: a.id,
      alert_code: a.code,
      created_at: now,
      status: "waiting",
      photos,
      meta: {
        observed_at: now,
        device_time: now,
        lat: fix?.lat ?? null,
        lon: fix?.lon ?? null,
        gps_accuracy_m: fix?.accuracy ?? null,
        outcome,
        observed_stage: outcome === "confirmed" && stage ? stage : null,
        notes: note || null,
        reason: outcome === "confirmed" ? null : notes.trim(),
        photo_sha256: hashes.every(Boolean) ? hashes : [],
      },
    };
    item.meta.client_uuid = item.client_uuid;
    await queueCapture(item);
    setMessage({ kind: "ok", text: t("field.saved_offline") });
    if (online) {
      await afterSave();
      nav("/field");
    }
  };

  return (
    <main className="f-main" data-testid="field-alert">
      <p><Link to="/field">{t("field.back")}</Link></p>
      <h1>{name}</h1>
      <p className="f-what">{t(`change.${a.candidate.change_type}`)}, {t("queue.acres", { acres: a.area_acres })}. {a.overdue ? t("queue.overdue", { date: fmtDate(a.due_at, i18n.language) }) : t("queue.due", { date: fmtDate(a.due_at, i18n.language) })}</p>
      <p className="f-instruction">{t("field.instruction")}</p>
      <p className="f-banner warn" data-testid="counsel-note">{t("field.counsel_note")} <small>{t("field.counsel_pending")}</small></p>

      <div className="f-map"><MapView boundaries={boundaries} changes={changes} height="240px" /></div>
      {centre && (
        <p className="f-loc">
          {t("field.location")}: {centre[1].toFixed(5)}, {centre[0].toFixed(5)}{" "}
          <a href={`geo:${centre[1].toFixed(6)},${centre[0].toFixed(6)}`}>{t("field.open_maps")}</a>
        </p>
      )}
      <div className="f-pair">
        <figure><ChipImage id={a.id} which="before" alt={t("detail.before")} /><figcaption>{t("detail.before")} {fmtDate(a.candidate.last_clear_at, i18n.language)}</figcaption></figure>
        <figure><ChipImage id={a.id} which="after" alt={t("detail.after")} /><figcaption>{t("detail.after")} {fmtDate(a.candidate.first_changed_at, i18n.language)}</figcaption></figure>
      </div>

      <section className="f-capture">
        <h2>{t("field.capture_title")}</h2>

        <label className="f-photo">
          {t("field.add_photo")}
          <input type="file" accept="image/*" capture="environment" multiple onChange={(e) => setPhotos([...photos, ...Array.from(e.target.files ?? [])])} data-testid="photo-input" />
        </label>
        {photos.length > 0 && <p data-testid="photo-count">{t("detail.photos", { count: photos.length })}</p>}

        {a.is_demo && (
          <label className="f-field">
            {t("field.demo_position")}
            <select value={posMode} onChange={(e) => { setPosMode(e.target.value as typeof posMode); setFix(null); }} data-testid="pos-mode">
              <option value="device">{t("field.pos_device")}</option>
              <option value="site">{t("field.pos_site")}</option>
              <option value="far">{t("field.pos_far")}</option>
            </select>
          </label>
        )}
        <button className="f-btn secondary" onClick={getPosition} data-testid="get-gps">{t("field.get_gps")}</button>
        {gpsError && <p className="f-banner stop">{gpsError}</p>}
        {fix && (
          <p data-testid="gps-fix">
            {fix.lat.toFixed(5)}, {fix.lon.toFixed(5)} (±{fix.accuracy} m){fix.simulated ? `, ${t("field.simulated")}` : ""}
          </p>
        )}
        {distance !== null && (
          distance > WARN_M
            ? <p className="f-banner warn" data-testid="distance-warning">{t("field.distance_warn", { m: distance })}</p>
            : <p className="f-banner ok" data-testid="distance-ok">{t("detail.distance", { m: distance })}</p>
        )}

        <fieldset className="f-outcome">
          <legend>{t("field.outcome")}</legend>
          {(["confirmed", "false_alarm", "cannot_access"] as const).map((o) => (
            <label key={o} className={outcome === o ? "on" : ""}>
              <input type="radio" name="outcome" value={o} checked={outcome === o} onChange={() => setOutcome(o)} data-testid={`outcome-${o}`} />
              {t(`field.outcome_${o}`)}
            </label>
          ))}
        </fieldset>
        {outcome === "confirmed" && (
          <label className="f-field">
            {t("field.stage")}
            <select value={stage} onChange={(e) => setStage(e.target.value)} data-testid="stage">
              <option value="">{t("form.choose")}</option>
              {["soil_dumped", "land_levelled", "sheds_fences", "building_rises", "occupied"].map((s) => <option key={s} value={s}>{t(`stage.${s}`)}</option>)}
            </select>
          </label>
        )}
        <label className="f-field">
          {outcome && outcome !== "confirmed" ? t("form.reason") : t("field.notes")}
          <textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} data-testid="notes" />
        </label>
        {message && <p className={`f-banner ${message.kind}`} role="status" data-testid="save-message">{message.text}</p>}
        <button className="f-btn" onClick={() => void save()} data-testid="save-visit">{t("field.save")}</button>
      </section>
    </main>
  );
}
