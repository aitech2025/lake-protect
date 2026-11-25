/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { api, fmtDateTime } from "../api";
import { isAdmin, useAuth } from "../auth";
import { useAsync, usePageTitle } from "../components/Bits";
import { PageState, TableRegion } from "../components/PageState";

/**
 * Satellite image sources (DECISIONS.md D-066). Everyone sees them; the admin adds, changes, turns
 * on or off, and deletes them. One optical and at most one radar source screen at a time; sharper
 * sources carry the price used for estimates. Detection thresholds are not here: they stay in the
 * versioned rule file.
 */
type Source = {
  id: number; key: string; name: string; provider: string; purpose: string; resolution_m: number; revisit_days: number | null;
  stac_url: string | null; collection: string | null; max_scene_cloud_pct: number | null; price_usd_per_sq_km: number | null;
  min_order_sq_km: number | null; licence_notice: string | null; notes: string | null; active: boolean;
  updated_at: string | null; updated_by: string | null;
};
const PURPOSES = ["screen_optical", "screen_radar", "sharper"] as const;
const EMPTY = { key: "", name: "", provider: "", purpose: "sharper", resolution_m: "", revisit_days: "", stac_url: "", collection: "",
  max_scene_cloud_pct: "", price_usd_per_sq_km: "", min_order_sq_km: "", licence_notice: "", notes: "", active: true };
type Form = typeof EMPTY;
const LABEL: Record<string, string> = {
  name: "sat.name", provider: "sat.provider", resolution_m: "sat.resolution", revisit_days: "sat.revisit", stac_url: "sat.stac_url",
  collection: "sat.collection", max_scene_cloud_pct: "sat.cloud", price_usd_per_sq_km: "sat.price", min_order_sq_km: "sat.min_order",
  licence_notice: "sat.licence", notes: "sat.notes", active: "sat.status",
};

function toForm(s: Source): Form {
  const v = (x: unknown) => (x === null || x === undefined ? "" : String(x));
  return { key: s.key, name: s.name, provider: s.provider, purpose: s.purpose, resolution_m: v(s.resolution_m), revisit_days: v(s.revisit_days),
    stac_url: v(s.stac_url), collection: v(s.collection), max_scene_cloud_pct: v(s.max_scene_cloud_pct), price_usd_per_sq_km: v(s.price_usd_per_sq_km),
    min_order_sq_km: v(s.min_order_sq_km), licence_notice: v(s.licence_notice), notes: v(s.notes), active: s.active };
}

function toBody(f: Form, creating: boolean) {
  const num = (x: string) => (x.trim() === "" ? null : Number(x));
  const body: Record<string, unknown> = {
    name: f.name, provider: f.provider, resolution_m: num(f.resolution_m), revisit_days: num(f.revisit_days),
    licence_notice: f.licence_notice || null, notes: f.notes || null, active: f.active,
  };
  if (f.purpose === "sharper") Object.assign(body, { price_usd_per_sq_km: num(f.price_usd_per_sq_km), min_order_sq_km: num(f.min_order_sq_km) });
  else Object.assign(body, { stac_url: f.stac_url || null, collection: f.collection || null });
  if (f.purpose === "screen_optical") body.max_scene_cloud_pct = num(f.max_scene_cloud_pct);
  if (creating) Object.assign(body, { key: f.key, purpose: f.purpose });
  return body;
}

export function Satellites() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const admin = isAdmin(user);
  const { data, error, status, loading, reload } = useAsync(() => api<{ items: Source[] }>("/satellites"), []);
  const history = useAsync(() => (admin ? api<{ items: any[] }>("/satellites/history") : Promise.resolve({ items: [] })), [admin]);
  const [editing, setEditing] = useState<number | "new" | null>(null);
  const [form, setForm] = useState<Form>(EMPTY);
  const [deleting, setDeleting] = useState<Source | null>(null);
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  usePageTitle(t("sat.title"));
  const items = data?.items ?? [];

  const done = (text: string) => {
    setMessage({ ok: true, text });
    setEditing(null);
    setDeleting(null);
    setReason("");
    reload();
    history.reload();
  };
  const fail = (e: unknown) => setMessage({ ok: false, text: String((e as Error).message) });

  const save = async (e: FormEvent) => {
    e.preventDefault();
    setMessage(null);
    try {
      const creating = editing === "new";
      const out = await api<any>(creating ? "/satellites" : `/satellites/${editing}`, { method: creating ? "POST" : "PATCH", json: toBody(form, creating) });
      done(out.switched_off?.length ? t("sat.saved_switched", { name: out.name, off: out.switched_off.join(", ") }) : t("sat.saved", { name: out.name }));
    } catch (err) {
      fail(err);
    }
  };
  const toggle = async (s: Source) => {
    setMessage(null);
    try {
      const out = await api<any>(`/satellites/${s.id}`, { method: "PATCH", json: { active: !s.active } });
      done(out.switched_off?.length ? t("sat.saved_switched", { name: out.name, off: out.switched_off.join(", ") })
        : t(out.active ? "sat.turned_on" : "sat.turned_off", { name: out.name }));
    } catch (err) {
      fail(err);
    }
  };
  const remove = async (e: FormEvent) => {
    e.preventDefault();
    if (!deleting) return;
    try {
      await api(`/satellites/${deleting.id}?reason=${encodeURIComponent(reason)}`, { method: "DELETE" });
      done(t("sat.deleted", { name: deleting.name }));
    } catch (err) {
      fail(err);
    }
  };
  const set = (k: keyof Form) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const editor = (
    <form className="panel sat-form" onSubmit={save} data-testid="sat-form">
      <h2 className="title-s">{editing === "new" ? t("sat.add") : t("sat.edit", { name: form.name })}</h2>
      <div className="sat-grid">
        {editing === "new" && (
          <>
            <label className="field">{t("sat.purpose")}
              <select value={form.purpose} onChange={set("purpose")} data-testid="sat-purpose">
                {PURPOSES.map((p) => <option key={p} value={p}>{t(`sat.purposes.${p}`)}</option>)}
              </select>
            </label>
            <label className="field">{t("sat.key")}<input value={form.key} onChange={set("key")} placeholder="planet-skysat" data-testid="sat-key" /></label>
          </>
        )}
        <label className="field">{t("sat.name")}<input value={form.name} onChange={set("name")} data-testid="sat-name" /></label>
        <label className="field">{t("sat.provider")}<input value={form.provider} onChange={set("provider")} data-testid="sat-provider" /></label>
        <label className="field">{t("sat.resolution")}<input type="number" step="0.01" min="0" value={form.resolution_m} onChange={set("resolution_m")} data-testid="sat-resolution" /></label>
        <label className="field">{t("sat.revisit")}<input type="number" step="0.1" min="0" value={form.revisit_days} onChange={set("revisit_days")} /></label>
        {form.purpose !== "sharper" && (
          <>
            <label className="field wide">{t("sat.stac_url")}<input value={form.stac_url} onChange={set("stac_url")} placeholder="https://" data-testid="sat-stac" /></label>
            <label className="field">{t("sat.collection")}<input value={form.collection} onChange={set("collection")} data-testid="sat-collection" /></label>
          </>
        )}
        {form.purpose === "screen_optical" && (
          <label className="field">{t("sat.cloud")}<input type="number" min="0" max="100" value={form.max_scene_cloud_pct} onChange={set("max_scene_cloud_pct")} data-testid="sat-cloud" /></label>
        )}
        {form.purpose === "sharper" && (
          <>
            <label className="field">{t("sat.price")}<input type="number" step="0.01" min="0" value={form.price_usd_per_sq_km} onChange={set("price_usd_per_sq_km")} data-testid="sat-price" /></label>
            <label className="field">{t("sat.min_order")}<input type="number" step="0.01" min="0" value={form.min_order_sq_km} onChange={set("min_order_sq_km")} /></label>
          </>
        )}
        <label className="field wide">{t("sat.licence")}<input value={form.licence_notice} onChange={set("licence_notice")} /></label>
        <label className="field wide">{t("sat.notes")}<textarea rows={2} value={form.notes} onChange={set("notes")} data-testid="sat-notes" /></label>
        <label className="check"><input type="checkbox" checked={form.active} onChange={(e) => setForm((f) => ({ ...f, active: e.target.checked }))} /> {t("sat.on")}</label>
      </div>
      <p className="small muted">{t(`sat.help.${form.purpose}`)}</p>
      <div className="officer-buttons">
        <button type="submit" className="btn" data-testid="sat-save">{t("sat.save")}</button>
        <button type="button" className="btn secondary" onClick={() => setEditing(null)}>{t("action.cancel")}</button>
      </div>
    </form>
  );

  return (
    <div className="page satellites" data-testid="satellites">
      <div className="page-head">
        <div>
          <h1>{t("sat.title")}</h1>
          <p className="muted">{t("sat.lede")}</p>
        </div>
        {admin && editing === null && (
          <button type="button" className="btn" onClick={() => { setForm(EMPTY); setEditing("new"); setMessage(null); }} data-testid="sat-add">{t("sat.add")}</button>
        )}
      </div>
      {message && <p className={`banner ${message.ok ? "info" : "stop"}`} role={message.ok ? "status" : "alert"} data-testid="sat-message">{message.text}</p>}
      {editing === "new" && editor}
      <PageState loading={loading && !data} error={error} status={status} onRetry={reload} />
      {PURPOSES.map((p) => {
        const rows = items.filter((s) => s.purpose === p);
        return (
          <section key={p} className="section" data-testid={`sat-group-${p}`}>
            <h2 className="title-s">{t(`sat.purposes.${p}`)}</h2>
            <p className="small muted">{t(`sat.help.${p}`)}</p>
            <TableRegion label={t(`sat.purposes.${p}`)}>
              <table className="grid">
                <thead>
                  <tr>
                    <th>{t("sat.name")}</th><th>{t("sat.provider")}</th><th>{t("sat.detail")}</th>
                    {p === "sharper" ? <th>{t("sat.price")}</th> : <th>{t("sat.catalogue")}</th>}
                    <th>{t("sat.status")}</th>{admin && <th />}
                  </tr>
                </thead>
                <tbody>
                  {rows.length === 0 && <tr><td colSpan={admin ? 6 : 5} className="muted">{t("sat.none")}</td></tr>}
                  {rows.map((s) => (
                    <tr key={s.id} data-testid={`sat-row-${s.key}`}>
                      <td><b>{s.name}</b><div className="small muted"><code>{s.key}</code></div>{s.notes && <div className="small muted">{s.notes}</div>}</td>
                      <td>{s.provider}</td>
                      <td className="small">
                        {t("sat.res_value", { m: s.resolution_m })}
                        {s.revisit_days !== null && <div>{t("sat.revisit_value", { d: s.revisit_days })}</div>}
                        {s.max_scene_cloud_pct !== null && <div>{t("sat.cloud_value", { p: s.max_scene_cloud_pct })}</div>}
                      </td>
                      {p === "sharper" ? (
                        <td className="small">{s.price_usd_per_sq_km === null ? t("sat.price_on_request") : t("sat.price_value", { usd: s.price_usd_per_sq_km })}
                          {s.min_order_sq_km !== null && <div>{t("sat.min_order_value", { km: s.min_order_sq_km })}</div>}</td>
                      ) : (
                        <td className="small"><code>{s.collection}</code><div className="muted sat-url">{s.stac_url}</div></td>
                      )}
                      <td>
                        <span className={`delivery ${s.active ? "sent" : "queued"}`}>{t(s.active ? "sat.on" : "sat.off")}</span>
                        {s.updated_at && <div className="small muted">{fmtDateTime(s.updated_at, i18n.language)}{s.updated_by ? `, ${s.updated_by}` : ""}</div>}
                      </td>
                      {admin && (
                        <td className="sat-actions">
                          <button type="button" className="btn secondary" onClick={() => { setForm(toForm(s)); setEditing(s.id); setMessage(null); }} data-testid={`sat-edit-${s.key}`}>{t("sat.edit_short")}</button>
                          <button type="button" className="btn secondary" onClick={() => void toggle(s)} data-testid={`sat-toggle-${s.key}`}>{t(s.active ? "sat.turn_off" : "sat.turn_on")}</button>
                          <button type="button" className="btn quiet" onClick={() => { setDeleting(s); setReason(""); setMessage(null); }} data-testid={`sat-delete-${s.key}`}>{t("sat.delete")}</button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableRegion>
            {typeof editing === "number" && rows.some((s) => s.id === editing) && editor}
            {deleting && deleting.purpose === p && (
              <form className="panel sat-form" onSubmit={remove} data-testid="sat-delete-form">
                <p className="banner warn">{t("sat.delete_warn", { name: deleting.name })}</p>
                <label className="field">{t("sat.reason")}<input value={reason} onChange={(e) => setReason(e.target.value)} data-testid="sat-reason" /></label>
                <div className="officer-buttons">
                  <button type="submit" className="btn danger" disabled={reason.trim().length < 5} data-testid="sat-delete-confirm">{t("sat.delete")}</button>
                  <button type="button" className="btn secondary" onClick={() => setDeleting(null)}>{t("action.cancel")}</button>
                </div>
              </form>
            )}
          </section>
        );
      })}
      <p className="note">{t("sat.thresholds")}</p>
      {admin && (history.data?.items.length ?? 0) > 0 && (
        <section className="section panel" data-testid="sat-history">
          <h2 className="title-s">{t("sat.history")}</h2>
          <ol className="report-history">
            {history.data!.items.map((h) => (
              <li key={h.id}>
                <span className="small muted">{fmtDateTime(h.at, i18n.language)} · {h.actor}</span>
                <span>{t(`sat.action.${h.action.split(".")[1]}`, { defaultValue: h.action })}: {h.details?.after?.name ?? h.details?.before?.name ?? h.source_name ?? h.details?.key ?? ""}
                  {h.details?.changed ? ` (${h.details.changed.map((f: string) => (LABEL[f] ? t(LABEL[f]) : f)).join(", ")})` : ""}{h.details?.reason ? `: ${h.details.reason}` : ""}</span>
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}
