/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { API_BASE, api, authHeaders, fmtDate, fmtDateTime } from "../api";
import { useAuth } from "../auth";

const PACK_STATES = ["FIELD_CONFIRMED", "AWAITING_BOUNDARY", "PACK_READY", "WITH_OFFICER", "ACTION_RECORDED", "CLOSED_NO_ACTION", "POST_ACTION_WATCH"];

async function openBlob(path: string, download?: string): Promise<void> {
  const res = await fetch(API_BASE + path, { headers: authHeaders() });
  if (!res.ok) throw new Error(`${res.status}`);
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  if (download) a.download = download;
  else a.target = "_blank";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

/** Section 6.7 checklist. The nodal and legal officers record each item; it informs, it does not decide. */
export function Checklist({ alert, onChange }: { alert: any; onChange: () => void }) {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const canEdit = user && ["nodal_officer", "legal_officer"].includes(user.role) && PACK_STATES.includes(alert.state);
  const gaps = alert.readiness.filter((r: any) => r.status === "no").map((r: any) => t(`checklist.${r.item_key}`));
  return (
    <section className="section panel" data-testid="checklist">
      <h2 className="title-s">{t("detail.checklist_title")}</h2>
      {gaps.length > 0 && <p className="banner warn" style={{ marginTop: "0.6rem" }}>{t("checklist_ui.gaps", { items: gaps.join("; ") })}</p>}
      <div className="check-list">
        {alert.readiness.map((r: any) => (
          <ChecklistRow key={r.item_key} alertId={alert.id} row={r} canEdit={Boolean(canEdit)} onChange={onChange} lang={i18n.language} />
        ))}
      </div>
    </section>
  );
}

function ChecklistRow({ alertId, row, canEdit, onChange, lang }: { alertId: number; row: any; canEdit: boolean; onChange: () => void; lang: string }) {
  const { t } = useTranslation();
  const [status, setStatus] = useState<string>(row.status ?? "");
  const [ref, setRef] = useState<string>(row.evidence_ref ?? "");
  const [error, setError] = useState<string | null>(null);
  const save = async () => {
    try {
      await api(`/alerts/${alertId}/readiness/${row.item_key}`, { method: "PUT", json: { status, evidence_ref: ref || null } });
      onChange();
    } catch (e) {
      setError((e as Error).message);
    }
  };
  return (
    <div className={`check-row ${canEdit ? "edit" : "read"}`} data-testid={`check-${row.item_key}`}>
      {canEdit ? (
        <>
          <span>
            {t(`checklist.${row.item_key}`)}
            {row.system_hint && <span className="small muted"> ({row.system_hint})</span>}
            {row.checked_by && <div className="small muted">{t("checklist_ui.checked", { name: row.checked_by, date: fmtDateTime(row.checked_at, lang) })}</div>}
          </span>
          <select className="control" value={status} onChange={(e) => setStatus(e.target.value)} aria-label={t(`checklist.${row.item_key}`)}>
            <option value="">{t("checklist.unset")}</option>
            <option value="yes">{t("checklist.yes")}</option>
            <option value="no">{t("checklist.no")}</option>
            <option value="not_applicable">{t("checklist.not_applicable")}</option>
          </select>
          <input className="control" value={ref} onChange={(e) => setRef(e.target.value)} placeholder={t("checklist_ui.evidence")} aria-label={t("checklist_ui.evidence")} />
          <button className="btn secondary" onClick={() => void save()} disabled={!status}>{t("checklist_ui.save")}</button>
          {error && <p className="error small check-row-error">{error}</p>}
        </>
      ) : (
        <>
          <b className={row.status === "no" ? "flag-overdue" : undefined}>{t(`checklist.${row.status ?? "unset"}`)}</b>
          <span>
            {t(`checklist.${row.item_key}`)}
            {row.evidence_ref && <span className="small muted">. {row.evidence_ref}</span>}
            {row.system_hint && <div className="small muted">{row.system_hint}</div>}
          </span>
        </>
      )}
    </div>
  );
}

/** Section 9.3: generate, open, download and check the evidence pack. */
export function CaseFilePanel({ alert, onChange }: { alert: any; onChange: () => void }) {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const [message, setMessage] = useState<{ kind: string; text: string } | null>(null);
  const canMake = user && ["nodal_officer", "legal_officer"].includes(user.role);
  const ready = PACK_STATES.includes(alert.state);
  const packs = [...alert.evidence_packs].reverse();

  const generate = async () => {
    try {
      const out = await api<any>(`/alerts/${alert.id}/evidence-pack`, { method: "POST" });
      setMessage({ kind: "info", text: t("pack.made", { v: out.version }) });
      onChange();
    } catch (e) {
      setMessage({ kind: "stop", text: (e as Error).message });
    }
  };
  const check = async (v: number) => {
    const out = await api<any>(`/alerts/${alert.id}/evidence-pack/verify?version=${v}`);
    setMessage(out.ok ? { kind: "info", text: t("pack.ok", { n: out.files_checked }) } : { kind: "stop", text: t("pack.bad", { problems: out.problems.join("; ") }) });
  };

  return (
    <div className="panel" data-testid="case-file">
      <h2 className="title-s">{t("pack.title")}</h2>
      {!ready && <p className="small muted" style={{ marginTop: "0.5rem" }}>{t("pack.needs_field")}</p>}
      {ready && packs.length === 0 && <p className="small muted" style={{ marginTop: "0.5rem" }}>{t("pack.none")}</p>}
      <ul style={{ listStyle: "none", padding: 0, margin: "0.6rem 0", display: "grid", gap: "0.6rem" }}>
        {packs.map((p: any) => (
          <li key={p.id} data-testid={`pack-v${p.version}`}>
            <b>{t("pack.version", { v: p.version, date: fmtDate(p.generated_at, i18n.language) })}</b>
            <div className={p.counsel_reviewed ? "small muted" : "small flag-overdue"}>{p.counsel_reviewed ? t("pack.reviewed") : t("pack.draft")}</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem", marginTop: "0.35rem" }}>
              <button className="btn secondary" onClick={() => void openBlob(`/alerts/${alert.id}/evidence-pack/pdf?version=${p.version}`)}>{t("pack.open_pdf")}</button>
              <button className="btn secondary" onClick={() => void openBlob(`/alerts/${alert.id}/evidence-pack?version=${p.version}`, `${alert.code}-v${p.version}.zip`)}>{t("pack.download")}</button>
              <button className="btn secondary" onClick={() => void check(p.version)} data-testid={`check-pack-v${p.version}`}>{t("pack.check")}</button>
            </div>
          </li>
        ))}
      </ul>
      {canMake && ready && <button className="btn" onClick={() => void generate()} data-testid="generate-pack">{t("pack.generate")}</button>}
      {message && <p className={`banner ${message.kind}`} role="status" style={{ marginTop: "0.6rem" }} data-testid="pack-message">{message.text}</p>}
    </div>
  );
}
