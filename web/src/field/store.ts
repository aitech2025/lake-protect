/** Offline store for the field app (section 9.2): alerts, details, image pairs and the capture queue. */
import { openDB, type DBSchema, type IDBPDatabase } from "idb";

export type QueuedCapture = {
  client_uuid: string;
  alert_id: number;
  alert_code: string;
  meta: Record<string, unknown>;
  photos: Blob[];
  created_at: string;
  status: "waiting" | "failed";
  error?: string;
};

interface FieldDB extends DBSchema {
  alerts: { key: number; value: Record<string, unknown> & { id: number } };
  details: { key: number; value: Record<string, unknown> & { id: number } };
  chips: { key: string; value: Blob };
  queue: { key: string; value: QueuedCapture };
  meta: { key: string; value: unknown };
}

let dbp: Promise<IDBPDatabase<FieldDB>> | null = null;

export function db(): Promise<IDBPDatabase<FieldDB>> {
  dbp ??= openDB<FieldDB>("lp-field", 1, {
    upgrade(d) {
      d.createObjectStore("alerts", { keyPath: "id" });
      d.createObjectStore("details", { keyPath: "id" });
      d.createObjectStore("chips");
      d.createObjectStore("queue", { keyPath: "client_uuid" });
      d.createObjectStore("meta");
    },
  });
  return dbp;
}

export async function clearAll(): Promise<void> {
  const d = await db();
  await Promise.all((["alerts", "details", "chips", "queue", "meta"] as const).map((s) => d.clear(s)));
}
