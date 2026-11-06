/** Download "My alerts" for offline use, and send queued captures when there is signal. */
import { API_BASE, authHeaders } from "../api";
import { centroidOf, tilesAround } from "./geo";
import { db, type QueuedCapture } from "./store";

/** Demo only: lets a presenter show "no signal" on one laptop, where airplane mode does not cut localhost. */
let pretendOffline = false;
const listeners = new Set<() => void>();

export function setPretendOffline(on: boolean): void {
  pretendOffline = on;
  listeners.forEach((l) => l());
}
export function isPretendOffline(): boolean {
  return pretendOffline;
}
export function onSyncChange(fn: () => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
function changed(): void {
  listeners.forEach((l) => l());
}

class Offline extends Error {}

async function get(path: string): Promise<Response> {
  if (pretendOffline) throw new Offline("no signal (demo)");
  let res: Response;
  try {
    res = await fetch(API_BASE + path, { headers: authHeaders(), cache: "no-store" });
  } catch {
    throw new Offline("no signal");
  }
  if (!res.ok) throw new Error(`${res.status}`);
  return res;
}

/** Refresh the offline copy. Returns false when there is no signal (the stored copy stays). */
export async function refreshAlerts(): Promise<boolean> {
  try {
    const list = (await (await get("/alerts")).json()).items as (Record<string, unknown> & { id: number; geometry: GeoJSON.Geometry })[];
    const d = await db();
    const active = list.filter((a) => a.state === "ASSIGNED");
    const tx = d.transaction(["alerts"], "readwrite");
    await tx.objectStore("alerts").clear();
    for (const a of active) await tx.objectStore("alerts").put(a);
    await tx.done;
    for (const a of active) {
      const detail = await (await get(`/alerts/${a.id}`)).json();
      await d.put("details", detail);
      for (const which of ["before", "after"]) {
        try {
          await d.put("chips", await (await get(`/alerts/${a.id}/chips/${which}`)).blob(), `${a.id}:${which}`);
        } catch (e) {
          if (e instanceof Offline) throw e;
        }
      }
      // Warm the service worker's tile cache around the change, so the small map works offline.
      const [lon, lat] = centroidOf(a.geometry);
      await Promise.all(tilesAround(lon, lat).map((u) => fetch(u).catch(() => undefined)));
    }
    await d.put("meta", new Date().toISOString(), "last_refresh");
    changed();
    return true;
  } catch (e) {
    if (e instanceof Offline) return false;
    throw e;
  }
}

export async function queueCapture(item: QueuedCapture): Promise<void> {
  await (await db()).put("queue", item);
  changed();
}

export async function queued(): Promise<QueuedCapture[]> {
  return (await db()).getAll("queue");
}

export type SyncResult = { sent: { client_uuid: string; alert_code: string; state: string; distance_warning: boolean; step_refused?: string }[]; failed: number; offline: boolean };

let running: Promise<SyncResult> | null = null;

/** Send every waiting capture. Safe to call often: the server ignores a client_uuid it already has. */
export function syncNow(): Promise<SyncResult> {
  running ??= (async () => {
    const out: SyncResult = { sent: [], failed: 0, offline: false };
    const d = await db();
    for (const item of await d.getAll("queue")) {
      if (pretendOffline) {
        out.offline = true;
        break;
      }
      const form = new FormData();
      form.append("meta", JSON.stringify(item.meta));
      item.photos.forEach((p, i) => form.append("photos", p, `photo-${i + 1}.${p.type.includes("png") ? "png" : "jpg"}`));
      let res: Response;
      try {
        res = await fetch(`${API_BASE}/alerts/${item.alert_id}/field-checks`, { method: "POST", headers: authHeaders(), body: form });
      } catch {
        out.offline = true;
        break;
      }
      if (res.ok) {
        const body = await res.json();
        await d.delete("queue", item.client_uuid);
        out.sent.push({ client_uuid: item.client_uuid, alert_code: item.alert_code, state: body.state, distance_warning: body.distance_warning, step_refused: body.step_refused });
      } else {
        let detail = res.statusText;
        try {
          detail = (await res.json()).detail;
        } catch {
          /* keep status */
        }
        await d.put("queue", { ...item, status: "failed", error: String(detail) });
        out.failed += 1;
      }
    }
    if (out.sent.length) await d.put("meta", out.sent, "last_sent");
    changed();
    return out;
  })().finally(() => {
    running = null;
  });
  return running;
}

export async function sha256Hex(blob: Blob): Promise<string | null> {
  if (!globalThis.crypto?.subtle) return null; // only in secure contexts; the server hashes anyway
  const digest = await crypto.subtle.digest("SHA-256", await blob.arrayBuffer());
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export function newUuid(): string {
  // randomUUID exists only in secure contexts, so check at run time.
  if (typeof (crypto as { randomUUID?: unknown }).randomUUID === "function") return crypto.randomUUID();
  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = [...b].map((x) => x.toString(16).padStart(2, "0")).join("");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}
