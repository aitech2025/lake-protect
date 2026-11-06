import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { API_BASE, authHeaders } from "../api";
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

/** Images behind login: fetched with the token, shown from a blob URL. */
export function AuthImage({ path, alt, className }: { path: string; alt: string; className?: string }) {
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let url: string | null = null;
    let live = true;
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
  }, [path]);
  if (failed) return <div className={className} role="img" aria-label={alt} />;
  return src ? <img src={src} alt={alt} className={className} /> : <div className={className} aria-busy="true" />;
}

export function LineSwatch({ colour, dash }: { colour: string; dash?: string }) {
  return (
    <svg width="26" height="10" aria-hidden="true">
      <line x1="1" y1="5" x2="25" y2="5" stroke={colour} strokeWidth="2.5" strokeDasharray={dash} />
    </svg>
  );
}

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]): { data: T | null; error: string | null; reload: () => void } {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let live = true;
    setError(null);
    fn()
      .then((d) => live && setData(d))
      .catch((e: Error) => live && setError(e.message));
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  return { data, error, reload: () => setTick((n) => n + 1) };
}
