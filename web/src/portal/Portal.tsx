/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, NavLink, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api";
import { MapView } from "../components/MapView";
import { BrandMark } from "../components/Brand";
import "./portal.css";

/**
 * The public side of GeoGuard (CONTEXT.md 17.8; DECISIONS.md D-062): report a problem on public
 * land, and check a report by its reference. No sign-in. English and Telugu. Real places in Telangana
 * only: the demo world is removed (D-065).
 */
type Lang = "en" | "te";
type L3 = { en: string; te: string };
type View = {
  ref: string; status: string; status_label: L3; what: string; what_label: L3; place: L3 | null; created_at: string;
  closed_reason: string | null; updates: boolean; events: { kind: string; status: string; note: L3; at: string }[];
};
type Config = { whats: { key: string; label: L3 }[]; updates: { sms_updates: boolean; whatsapp: boolean }; stats: { received: number; checking: number; closed: number } };

const LANGS: { code: Lang; label: string }[] = [{ code: "en", label: "English" }, { code: "te", label: "తెలుగు" }];
const KEY = "gg.portal.lang";

function usePortalLang(): [Lang, (l: Lang) => void] {
  const [lang, set] = useState<Lang>(() => {
    try {
      const v = localStorage.getItem(KEY);
      return v === "te" ? v : "en";
    } catch {
      return "en";
    }
  });
  const change = (l: Lang) => {
    set(l);
    try {
      localStorage.setItem(KEY, l);
    } catch {
      /* a convenience only */
    }
  };
  return [lang, change];
}

function fmt(value: string, lang: Lang, withTime = false): string {
  const locale = lang === "te" ? "te-IN" : "en-IN";
  const opts: Intl.DateTimeFormatOptions = withTime
    ? { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }
    : { day: "numeric", month: "short", year: "numeric" };
  return new Date(value).toLocaleString(locale, opts);
}

function Shell({ lang, setLang, children }: { lang: Lang; setLang: (l: Lang) => void; children: ReactNode }) {
  const { i18n } = useTranslation();
  const t = i18n.getFixedT(lang);
  useEffect(() => {
    document.title = `${t("citizen.title")} · GeoGuard`;
  }, [t]);
  return (
    <div className={`portal lang-${lang}`} lang={lang} data-testid="portal">
      <header className="portal-head">
        <Link to="/report" className="brand">
          <BrandMark />
          <span className="brand-copy">
            <span className="brand-name">GeoGuard</span>
            <span className="brand-tag">{t("citizen.tagline")}</span>
          </span>
        </Link>
        <div className="portal-langs" role="group" aria-label={t("citizen.language")}>
          {LANGS.map((l) => (
            <button key={l.code} type="button" lang={l.code} aria-pressed={lang === l.code} onClick={() => setLang(l.code)} data-testid={`lang-${l.code}`}>
              {l.label}
            </button>
          ))}
        </div>
      </header>
      <nav className="portal-tabs" aria-label="GeoGuard">
        <div className="portal-tabs-inner">
          <NavLink to="/report" end data-testid="tab-report">{t("citizen.tab_report")}</NavLink>
          <NavLink to="/report/track" data-testid="tab-track">{t("citizen.tab_track")}</NavLink>
        </div>
      </nav>
      <main className="portal-main">{children}</main>
      <footer className="portal-foot">
        <h2>{t("citizen.privacy_title")}</h2>
        <p>{t("citizen.privacy")}</p>
        <p>{t("citizen.not_finding")}</p>
        <p>{t("citizen.other_ways")} {t("citizen.whatsapp_soon")}</p>
        <p className="portal-links">
          <Link to="/login">{t("citizen.staff")}</Link>
        </p>
      </footer>
    </div>
  );
}

function errorText(e: unknown): string {
  return e instanceof ApiError ? e.message : String((e as Error).message ?? e);
}

export function ReportPage() {
  const [lang, setLang] = usePortalLang();
  const { i18n } = useTranslation();
  const t = i18n.getFixedT(lang);
  const [cfg, setCfg] = useState<Config | null>(null);
  const [pin, setPin] = useState<[number, number] | null>(null);
  const [fit, setFit] = useState<[number, number, number, number] | null>(null);
  const [locating, setLocating] = useState<string | null>(null);
  const [landmark, setLandmark] = useState("");
  const [what, setWhat] = useState("");
  const [photos, setPhotos] = useState<File[]>([]);
  const [description, setDescription] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [verifiedTo, setVerifiedTo] = useState<string | null>(null);
  const [consent, setConsent] = useState(false);
  const [phoneNote, setPhoneNote] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<View | null>(null);
  const [copied, setCopied] = useState(false);
  const previews = useMemo(() => photos.map((f) => URL.createObjectURL(f)), [photos]);
  useEffect(() => () => previews.forEach((u) => URL.revokeObjectURL(u)), [previews]);

  useEffect(() => {
    api<Config>("/citizen/config").then(setCfg).catch(() => setCfg(null));
  }, [done]);

  const locate = () => {
    if (!navigator.geolocation) {
      setLocating(t("citizen.location_failed"));
      return;
    }
    setLocating(t("citizen.locating"));
    navigator.geolocation.getCurrentPosition(
      (p) => {
        const ll: [number, number] = [Number(p.coords.longitude.toFixed(6)), Number(p.coords.latitude.toFixed(6))];
        setPin(ll);
        setFit([ll[0] - 0.004, ll[1] - 0.004, ll[0] + 0.004, ll[1] + 0.004]);
        setLocating(null);
      },
      () => setLocating(t("citizen.location_failed")),
      { enableHighAccuracy: true, timeout: 15000 },
    );
  };

  const sendCode = async () => {
    setPhoneNote(null);
    try {
      const out = await api<any>("/citizen/otp", { json: { phone } });
      setCodeSent(true);
      setSentTo(out.to ?? null);
    } catch (e) {
      setPhoneNote(errorText(e));
    }
  };
  const verify = async () => {
    setPhoneNote(null);
    try {
      const out = await api<{ token: string }>("/citizen/otp/verify", { json: { phone, code } });
      setToken(out.token);
      setVerifiedTo(sentTo ?? phone);
    } catch (e) {
      setPhoneNote(errorText(e));
    }
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setProblem(null);
    if (!pin) return setProblem(t("citizen.need_place"));
    if (!what) return setProblem(t("citizen.need_what"));
    if (token && !consent) return setProblem(t("citizen.need_consent"));
    const form = new FormData();
    form.append("data", JSON.stringify({
      language: lang, what, lon: pin[0], lat: pin[1], location_text: landmark || null, description: description || null,
      name: token ? name || null : null, phone_token: token && consent ? token : null,
    }));
    photos.forEach((f) => form.append("photos", f));
    setBusy(true);
    try {
      setDone(await api<View>("/citizen/reports", { body: form }));
    } catch (err) {
      setProblem(t("citizen.failed", { why: errorText(err) }));
    } finally {
      setBusy(false);
    }
  };

  const reset = () => {
    setDone(null); setPin(null); setFit(null); setLandmark(""); setWhat(""); setPhotos([]); setDescription("");
    setCode(""); setCodeSent(false); setToken(null); setVerifiedTo(null); setConsent(false); setCopied(false);
  };

  if (done) {
    return (
      <Shell lang={lang} setLang={setLang}>
        <section className="portal-card done" data-testid="report-done">
          <h1>{t("citizen.thanks")}</h1>
          <p>{t("citizen.your_ref")}</p>
          <p className="ref" data-testid="report-ref">{done.ref}</p>
          <button type="button" className="btn secondary" onClick={() => { void navigator.clipboard?.writeText(done.ref); setCopied(true); }}>
            {copied ? t("citizen.copied") : t("citizen.copy")}
          </button>
          <p className="muted">{t("citizen.keep_ref")}</p>
          <ol className="portal-timeline">
            {done.events.map((ev, i) => <li key={i}><span>{ev.note[lang]}</span></li>)}
          </ol>
          <p className="portal-actions">
            <Link className="btn" to={`/report/track/${done.ref}`} data-testid="see-status">{t("citizen.see_status")}</Link>
            <button type="button" className="btn secondary" onClick={reset}>{t("citizen.another")}</button>
          </p>
        </section>
      </Shell>
    );
  }

  return (
    <Shell lang={lang} setLang={setLang}>
      <section className="portal-intro">
        <h1>{t("citizen.title")}</h1>
        <p>{t("citizen.lede")}</p>
        {cfg && <p className="muted small" data-testid="portal-stats">{t("citizen.stats", cfg.stats)}</p>}
      </section>
      <form className="portal-form" onSubmit={(e) => void submit(e)} noValidate>
        <fieldset className="portal-card">
          <legend>{t("citizen.step_place")}</legend>
          <p className="muted">{t("citizen.place_help")}</p>
          <div className="portal-map">
            <MapView draft={pin ? [pin] : []} fit={fit} onMapClick={(p) => setPin(p)} testId="portal-map" />
          </div>
          <p className="small muted">{t("citizen.map_note")}</p>
          <div className="portal-row">
            <button type="button" className="btn secondary" onClick={locate}>{t("citizen.use_location")}</button>
            <span className="small" role="status" data-testid="pin-status">
              {pin ? t("citizen.pinned", { lat: pin[1].toFixed(5), lon: pin[0].toFixed(5) }) : locating}
            </span>
          </div>
          <label className="field">{t("citizen.landmark")}<input value={landmark} onChange={(e) => setLandmark(e.target.value)} maxLength={300} /></label>
        </fieldset>

        <fieldset className="portal-card">
          <legend>{t("citizen.step_what")}</legend>
          <div className="portal-whats">
            {(cfg?.whats ?? []).map((w) => (
              <label key={w.key} className={`portal-what${what === w.key ? " on" : ""}`} data-testid={`what-${w.key}`}>
                <input type="radio" name="what" value={w.key} checked={what === w.key} onChange={() => setWhat(w.key)} />
                <span>{w.label[lang]}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset className="portal-card">
          <legend>{t("citizen.step_photo")}</legend>
          <p className="small muted">{t("citizen.photo_note")}</p>
          <div className="portal-photos">
            {previews.map((u, i) => (
              <figure key={u}>
                <img src={u} alt="" />
                <button type="button" className="btn quiet" onClick={() => setPhotos((ps) => ps.filter((_, j) => j !== i))}>{t("citizen.remove_photo")}</button>
              </figure>
            ))}
          </div>
          {photos.length < 3 && (
            <label className="btn secondary portal-file">
              {t("citizen.add_photo")}
              <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) setPhotos((ps) => [...ps, f].slice(0, 3));
                e.target.value = "";
              }} data-testid="photo-input" />
            </label>
          )}
        </fieldset>

        <fieldset className="portal-card">
          <legend>{t("citizen.step_describe")}</legend>
          <label className="field">{t("citizen.describe_help")}
            <textarea rows={3} maxLength={1000} value={description} onChange={(e) => setDescription(e.target.value)} data-testid="description" />
          </label>
        </fieldset>

        <fieldset className="portal-card">
          <legend>{t("citizen.step_updates")}</legend>
          {cfg && !cfg.updates.sms_updates ? (
            <p className="note" data-testid="updates-unavailable">{t("citizen.updates_unavailable")}</p>
          ) : verifiedTo ? (
            <>
              <p className="ok" data-testid="phone-verified">{t("citizen.verified", { to: verifiedTo })}</p>
              <label className="field">{t("citizen.name")}<input value={name} onChange={(e) => setName(e.target.value)} maxLength={120} /></label>
              <label className="check"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} data-testid="consent" /> {t("citizen.consent")}</label>
            </>
          ) : (
            <>
              <p className="small muted">{t("citizen.updates_help")}</p>
              <div className="portal-row">
                <label className="field grow">{t("citizen.phone")}<input type="tel" inputMode="tel" value={phone} onChange={(e) => setPhone(e.target.value)} data-testid="phone" /></label>
                <button type="button" className="btn secondary" disabled={phone.replace(/\D/g, "").length < 10} onClick={() => void sendCode()} data-testid="send-code">{t("citizen.send_code")}</button>
              </div>
              {codeSent && (
                <div className="portal-row">
                  <label className="field grow">{t("citizen.code")}<input inputMode="numeric" maxLength={6} value={code} onChange={(e) => setCode(e.target.value)} data-testid="code" /></label>
                  <button type="button" className="btn secondary" disabled={code.length !== 6} onClick={() => void verify()} data-testid="verify-code">{t("citizen.verify")}</button>
                </div>
              )}
            </>
          )}
          {phoneNote && <p className="flag" role="alert">{phoneNote}</p>}
        </fieldset>

        {problem && <p className="banner stop" role="alert" data-testid="report-problem">{problem}</p>}
        <p className="portal-actions">
          <button type="submit" className="btn big" disabled={busy} data-testid="report-submit">{busy ? t("citizen.sending") : t("citizen.submit")}</button>
        </p>
      </form>
    </Shell>
  );
}

export function TrackPage() {
  const { ref: routeRef } = useParams();
  const nav = useNavigate();
  const [lang, setLang] = usePortalLang();
  const { i18n } = useTranslation();
  const t = i18n.getFixedT(lang);
  const [ref, setRef] = useState(routeRef ?? "");
  const [view, setView] = useState<View | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    setView(null);
    setMissing(false);
    if (!routeRef) return;
    api<View>(`/citizen/reports/${encodeURIComponent(routeRef)}`).then(setView).catch(() => setMissing(true));
  }, [routeRef]);

  return (
    <Shell lang={lang} setLang={setLang}>
      <section className="portal-card">
        <h1>{t("citizen.tab_track")}</h1>
        <form className="portal-row" onSubmit={(e) => { e.preventDefault(); if (ref.trim()) nav(`/report/track/${ref.trim().toUpperCase()}`); }}>
          <label className="field grow">{t("citizen.track_help")}
            <input value={ref} onChange={(e) => setRef(e.target.value)} placeholder="GGR-XXXX-XXXX" data-testid="track-ref" />
          </label>
          <button type="submit" className="btn" data-testid="track-go">{t("citizen.check")}</button>
        </form>
        {missing && <p className="flag" role="alert">{t("citizen.not_found")}</p>}
      </section>
      {view && (
        <section className="portal-card" data-testid="track-view">
          <p className="ref">{view.ref}</p>
          <p className={`portal-status s-${view.status}`} data-testid="track-status">{t("citizen.status_now", { status: view.status_label[lang] })}</p>
          <p>{t("citizen.reported", { date: fmt(view.created_at, lang), what: view.what_label[lang] })}</p>
          {view.place && <p>{t("citizen.place", { place: view.place[lang] })}</p>}
          <h2>{t("citizen.history")}</h2>
          <ol className="portal-timeline" data-testid="track-events">
            {view.events.map((ev, i) => (
              <li key={i}>
                <time>{fmt(ev.at, lang, true)}</time>
                <span>{ev.note[lang]}</span>
              </li>
            ))}
          </ol>
        </section>
      )}
    </Shell>
  );
}
