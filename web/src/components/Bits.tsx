import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { API_BASE, ApiError, authHeaders } from "../api";
import { certainty, GROUP_OF } from "./labels";

/** The boundary badge: its line style matches the boundary's line on the map (rule 2). */
export function BoundarySeal({ status, version }: { status: string | null; version?: number | null }) {
  const { t } = useTranslation();
  const kind = certainty(status);
  const dash = kind === "confirmed" ? undefined : kind === "preliminary" ? "6 4" : "1.5 4";
  return (
    <span className={`seal ${kind}`} data-testid="boundary-seal" data-certainty={kind}>
      <svg width="34" height="14" aria-hidden="true">
        <line x1="2" y1="7" x2="32" y2="7" stroke="currentColor" strokeWidth="3" strokeDasharray={dash} strokeLinecap="round" />
      </svg>
      <span>
        {status ? t(`boundary.${status}`) : "?"}
        <small>{kind === "confirmed" ? t("boundary.confirmed") : t("boundary.unconfirmed")}</small>
        {version ? <small>{t("boundary.version", { v: version })}</small> : null}
      </span>
    </span>
  );
}

export function StatePill({ state }: { state: string }) {
  const { t } = useTranslation();
  return <span className={`pill ${GROUP_OF[state] ?? "closed"}`} data-state={state}>{t(`state.${state}`)}</span>;
}

/**
 * Images behind login: fetched with the token, shown from a blob URL.
 * With `frame`, the image keeps its square while it loads and if it fails, and says which it is,
 * so evidence never silently disappears (UI audit A2).
 */
export function AuthImage({ path, alt, className, frame = false }: { path: string; alt: string; className?: string; frame?: boolean }) {
  const { t } = useTranslation();
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let url: string | null = null;
    let live = true;
    setFailed(false);
    setSrc(null);
    fetch(API_BASE + path, { headers: authHeaders() })
      .then((r) => (r.ok ? r.blob() : Promise.reject(new Error(String(r.status)))))
      .then((b) => {
        if (!live) return;
        url = URL.createObjectURL(b);
        setSrc(url);
      })
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [path, attempt]);
  if (!frame) {
    if (failed) return <div className={className} role="img" aria-label={alt} />;
    return src ? <img src={src} alt={alt} className={className} /> : <div className={className} aria-busy="true" />;
  }
  return (
    <div className={`evidence-frame${failed ? " failed" : ""}`} aria-busy={!src && !failed}>
      {src ? (
        <img src={src} alt={alt} className={className} />
      ) : failed ? (
        <div className="evidence-note" role="status">
          <p>{t("error.image_failed")}</p>
          <button type="button" className="btn secondary" onClick={() => setAttempt((n) => n + 1)}>{t("error.retry")}</button>
        </div>
      ) : (
        <p className="evidence-note">{t("error.image_loading")}</p>
      )}
    </div>
  );
}

export function LineSwatch({ colour, dash }: { colour: string; dash?: string }) {
  return (
    <svg width="26" height="10" aria-hidden="true">
      <line x1="1" y1="5" x2="25" y2="5" stroke={colour} strokeWidth="2.5" strokeDasharray={dash} />
    </svg>
  );
}

/** Sets the browser tab title for a page, "<page> · Lake Protect", so each route is identifiable (UI audit A4). */
export function usePageTitle(title: string | null | undefined): void {
  const { t } = useTranslation();
  const app = t("app.name");
  useEffect(() => {
    document.title = title ? `${title} · ${app}` : app;
  }, [title, app]);
}

type AsyncState<T> = { data: T | null; error: string | null; status: number | null; loading: boolean; reload: () => void };

/**
 * Loads data for a page. Besides data and error it reports `loading` and the HTTP `status` of a
 * failure, so pages can tell "not loaded yet", "not allowed" (403) and "not found" (404) apart from
 * an empty result (UI audit A1). Data from the previous load stays on screen while reloading.
 */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let live = true;
    setError(null);
    setStatus(null);
    setLoading(true);
    fn()
      .then((d) => {
        if (!live) return;
        setData(d);
        setLoading(false);
      })
      .catch((e: Error) => {
        if (!live) return;
        setError(e.message);
        setStatus(e instanceof ApiError ? e.status : null);
        setLoading(false);
      });
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  return { data, error, status, loading, reload: () => setTick((n) => n + 1) };
}
