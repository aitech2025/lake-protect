import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../api";
import { usePageTitle } from "../components/Bits";
import { MapView } from "../components/MapView";
import "./whatsapp-test.css";

type ChatLine = { id: number; from: "user" | "bot"; text: string; location?: [number, number] };
type Whats = { key: string; label: { en: string; te: string } };
type Reply = {
  replies: string[];
  state: string;
  report: null | { id: number; ref: string; alert_id: number | null; longitude: number | null; latitude: number | null; what: string; description: string | null; location_text: string | null };
};

const SAMPLE_PIN: [number, number] = [78.4867, 17.385];

export function WhatsAppTest() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === "te" ? "te" : "en";
  const [sender, setSender] = useState(() => `1555${String(Math.floor(Math.random() * 1_000_000_000)).padStart(9, "0")}`);
  const [state, setState] = useState("new");
  const [lines, setLines] = useState<ChatLine[]>([]);
  const [text, setText] = useState("");
  const [pin, setPin] = useState<[number, number] | null>(null);
  const [choices, setChoices] = useState<Whats[]>([]);
  const [report, setReport] = useState<Reply["report"]>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  usePageTitle(t("whatsapp_test.title"));

  useEffect(() => {
    let live = true;
    api<{ whats: Whats[] }>("/citizen/config").then((r) => live && setChoices(r.whats)).catch(() => undefined);
    return () => { live = false; };
  }, []);
  useEffect(() => endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }), [lines]);

  const call = async (message: { type: "text"; text: string } | { type: "location"; latitude: number; longitude: number }, display: string, location?: [number, number]) => {
    if (busy) return;
    setBusy(true);
    setError(null);
    setLines((old) => [...old, { id: Date.now(), from: "user", text: display, location }]);
    try {
      const out = await api<Reply>("/citizen/whatsapp/simulator", { json: { sender, ...message } });
      setState(out.state);
      setReport(out.report);
      setLines((old) => [...old, ...out.replies.map((reply, i) => ({ id: Date.now() + i + 1, from: "bot" as const, text: reply }))]);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const sendText = (value = text) => {
    if (!value.trim()) return;
    setText("");
    void call({ type: "text", text: value.trim() }, value.trim());
  };
  const sendPin = () => {
    if (!pin) return;
    const [longitude, latitude] = pin;
    void call({ type: "location", longitude, latitude }, t("whatsapp_test.pin_sent"), pin);
  };
  const start = () => {
    setLines([]);
    setReport(null);
    setState("new");
    void call({ type: "text", text: "Hi" }, "Hi");
  };
  const reset = () => {
    setReport(null);
    sendText("RESTART");
  };
  const send = (e: FormEvent) => { e.preventDefault(); sendText(); };

  const quickReplies = useMemo(() => {
    if (state === "lang") return [{ label: t("whatsapp_test.english"), value: "1" }, { label: t("whatsapp_test.telugu"), value: "2" }];
    if (state === "what") return choices.map((c, i) => ({ label: `${i + 1}. ${c.label[lang] || c.label.en}`, value: String(i + 1) }));
    if (state === "photo" || state === "describe") return [{ label: t("whatsapp_test.skip"), value: "SKIP" }];
    if (state === "updates") return [{ label: t("whatsapp_test.yes"), value: "YES" }, { label: t("whatsapp_test.no"), value: "NO" }];
    return [];
  }, [choices, lang, state, t]);

  return (
    <div className="page whats-test" data-testid="whatsapp-test">
      <div className="page-head">
        <div>
          <p className="whats-eyebrow">{t("whatsapp_test.eyebrow")}</p>
          <h1>{t("whatsapp_test.title")}</h1>
          <p className="muted">{t("whatsapp_test.intro")}</p>
        </div>
        <label className="field whats-sender">{t("whatsapp_test.sender")}
          <input value={sender.slice(4)} inputMode="numeric" pattern="[0-9]{7,9}" maxLength={9} onChange={(e) => { setSender(`1555${e.target.value.replace(/\D/g, "").slice(0, 9)}`); setLines([]); setState("new"); setReport(null); }} aria-describedby="sender-help" />
          <small id="sender-help">{t("whatsapp_test.sender_help")}</small>
        </label>
      </div>

      <p className="whats-safe"><b>{t("whatsapp_test.test_only")}</b> {t("whatsapp_test.isolation")}</p>

      <div className="whats-layout">
        <section className="whats-phone panel" aria-label={t("whatsapp_test.conversation")}>
          <header className="whats-phone-head">
            <span className="whats-avatar" aria-hidden="true">G</span>
            <span><b>GeoGuard</b><small>{t("whatsapp_test.simulated_chat")}</small></span>
            {lines.length > 0 && <button type="button" className="btn quiet" onClick={reset} disabled={busy}>{t("whatsapp_test.restart")}</button>}
          </header>
          <div className="whats-messages" aria-live="polite" aria-relevant="additions text">
            {lines.length === 0 && <div className="whats-empty"><b>{t("whatsapp_test.ready_title")}</b><span>{t("whatsapp_test.ready_text")}</span><button type="button" className="btn" onClick={start} disabled={busy}>{t("whatsapp_test.start")}</button></div>}
            {lines.map((line) => (
              <div key={line.id} className={`whats-line ${line.from}`}>
                <p>{line.text}</p>
                {line.location && <small>{line.location[1].toFixed(6)}, {line.location[0].toFixed(6)}</small>}
              </div>
            ))}
            <div ref={endRef} />
          </div>
          {quickReplies.length > 0 && (
            <div className="whats-quick" aria-label={t("whatsapp_test.quick_replies")}>
              {quickReplies.map((q) => <button key={q.value} className="chip" type="button" onClick={() => sendText(q.value)} disabled={busy}>{q.label}</button>)}
            </div>
          )}
          <form className="whats-composer" onSubmit={send}>
            <input value={text} onChange={(e) => setText(e.target.value)} placeholder={t("whatsapp_test.message_placeholder")} aria-label={t("whatsapp_test.message_placeholder")} disabled={!lines.length || busy} />
            <button className="btn" type="submit" disabled={!lines.length || !text.trim() || busy}>{busy ? t("whatsapp_test.sending") : t("whatsapp_test.send")}</button>
          </form>
          {error && <p className="banner stop" role="alert">{error}</p>}
        </section>

        <aside className="whats-side">
          <section className="panel whats-pin-panel">
            <div className="whats-section-head"><div><p className="whats-eyebrow">{t("whatsapp_test.location_step")}</p><h2>{t("whatsapp_test.pin_title")}</h2></div><button type="button" className="btn quiet" onClick={() => setPin(SAMPLE_PIN)}>{t("whatsapp_test.sample_pin")}</button></div>
            <p className="small muted">{t("whatsapp_test.pin_help")}</p>
            <div className="whats-map"><MapView draft={pin ? [pin] : []} onMapClick={setPin} testId="whatsapp-test-map" /></div>
            <div className="whats-pin-footer">
              <span className="small">{pin ? `${pin[1].toFixed(6)}, ${pin[0].toFixed(6)}` : t("whatsapp_test.no_pin")}</span>
              <button type="button" className="btn secondary" onClick={sendPin} disabled={!pin || state !== "place" || busy}>{t("whatsapp_test.send_pin")}</button>
            </div>
          </section>

          <section className="panel whats-result">
            <p className="whats-eyebrow">{t("whatsapp_test.result")}</p>
            {!report ? <p className="small muted">{t("whatsapp_test.result_waiting")}</p> : (
              <>
                <h2>{t("whatsapp_test.created", { ref: report.ref })}</h2>
                <p className="small">{report.latitude !== null && report.longitude !== null ? `${report.latitude.toFixed(6)}, ${report.longitude.toFixed(6)}` : t("whatsapp_test.location_words")}</p>
                <div className="whats-result-links">
                  <Link className="btn secondary" to={`/reports/${report.id}`}>{t("whatsapp_test.open_report")}</Link>
                  {report.alert_id && <Link className="btn" to={`/alerts/${report.alert_id}`}>{t("whatsapp_test.open_incident")}</Link>}
                </div>
              </>
            )}
          </section>
          <details className="panel whats-steps">
            <summary>{t("whatsapp_test.flow_title")}</summary>
            <ol><li>{t("whatsapp_test.flow_language")}</li><li>{t("whatsapp_test.flow_place")}</li><li>{t("whatsapp_test.flow_what")}</li><li>{t("whatsapp_test.flow_detail")}</li><li>{t("whatsapp_test.flow_created")}</li></ol>
            <p className="small muted">{t("whatsapp_test.no_photo_download")}</p>
          </details>
        </aside>
      </div>
    </div>
  );
}
