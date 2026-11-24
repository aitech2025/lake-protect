export const API_BASE = "/api";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

let token: string | null = null;
try {
  token = localStorage.getItem("lp.token");
} catch {
  token = null;
}

export function getToken(): string | null {
  return token;
}

export function setToken(value: string | null): void {
  token = value;
  try {
    if (value) localStorage.setItem("lp.token", value);
    else localStorage.removeItem("lp.token");
  } catch {
    /* the session still works for this tab */
  }
}

export function authHeaders(): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function api<T = unknown>(path: string, opts: { method?: string; json?: unknown; body?: BodyInit } = {}): Promise<T> {
  const headers: Record<string, string> = { ...authHeaders() };
  let body = opts.body;
  if (opts.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.json);
  }
  const res = await fetch(API_BASE + path, { method: opts.method ?? (body ? "POST" : "GET"), headers, body });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    } catch {
      /* keep status text */
    }
    throw new ApiError(res.status, detail);
  }
  const type = res.headers.get("content-type") ?? "";
  return (type.includes("json") ? res.json() : res.blob()) as Promise<T>;
}

export function fmtDate(value: string | null | undefined, lang = "en"): string {
  if (!value) return "";
  const d = new Date(value.length === 10 ? value + "T00:00:00Z" : value);
  return d.toLocaleDateString(lang === "te" ? "te-IN" : "en-IN", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
}

export function fmtDateTime(value: string | null | undefined, lang = "en"): string {
  if (!value) return "";
  return new Date(value).toLocaleString(lang === "te" ? "te-IN" : "en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

export type User = { id: number; username: string; name: string; role: string; language: string; is_demo: boolean };

export type AlertRow = {
  id: number;
  code: string;
  state: string;
  resolution: string | null;
  closed_at: string | null;
  related_alert_id: number | null;
  mode: string;
  cohort: string;
  priority_score: number | null;
  is_demo: boolean;
  created_at: string;
  asset_id: number;
  asset_name: string;
  asset_name_te: string | null;
  asset_type: string;
  change_type: string;
  change_label: string;
  summary: string;
  stage_estimate: string | null;
  area_sq_m: number;
  area_acres: number;
  first_changed_at: string;
  last_clear_at: string | null;
  sensor_basis: string;
  zone: string | null;
  alert_class: string | null;
  legal_verdict: string | null;
  review_count: number;
  last_review_outcome: string | null;
  court_matter: boolean;
  boundary_confirmed: boolean;
  permit_conflict: boolean;
  lon: number;
  lat: number;
  geometry: GeoJSON.Geometry;
  flags: string[];
};
