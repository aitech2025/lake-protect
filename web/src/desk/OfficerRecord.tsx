/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api, fmtDate } from "../api";
import { useAuth } from "../auth";

const FIELDS = [
  ["notice_ref", "text"],
  ["notice_date", "date"],
  ["hearing_date", "date"],
  ["order_ref", "text"],
  ["order_date", "date"],
  ["action_date", "date"],
] as const;

/** Section 9.1: notice, hearing, order and action fields. No suggested outcome. */
export function OfficerRecordPanel({ alert, onChange }: { alert: any; onChange: () => void }) {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const [values, setValues] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<{ kind: string; text: string } | null>(null);
  const canRecord = user && ["legal_officer", "senior_officer"].includes(user.role) && alert.state === "WITH_OFFICER";
  if (!canRecord && alert.officer_records.length === 0) return null;

  const save = async (recordAction: boolean) => {
    const body: Record<string, unknown> = { record_action: recordAction };
    for (const [k, v] of Object.entries(values)) if (v) body[k] = v;
    try {
      await api(`/alerts/${alert.id}/officer-record`, { json: body });
      setMessage({ kind: "info", text: recordAction ? t("officer.recorded") : t("officer.saved") });
      setValues({});
      onChange();
    } catch (e) {
      setMessage({ kind: "stop", text: (e as Error).message });
    }
  };

  return (
    <div className="panel" data-testid="officer-record">
      <h3>{t("officer.title")}</h3>
      {alert.officer_records.map((r: any) => (
        <dl key={r.id} className="facts small" style={{ marginTop: "0.6rem" }}>
          {r.notice_ref && <><dt>{t("officer.notice_ref")}</dt><dd>{r.notice_ref} {fmtDate(r.notice_date, i18n.language)}</dd></>}
          {r.hearing_date && <><dt>{t("officer.hearing_date")}</dt><dd>{fmtDate(r.hearing_date, i18n.language)}</dd></>}
          {r.order_ref && <><dt>{t("officer.order_ref")}</dt><dd>{r.order_ref} {fmtDate(r.order_date, i18n.language)}</dd></>}
          {r.action_date && <><dt>{t("officer.action_date")}</dt><dd>{fmtDate(r.action_date, i18n.language)}</dd></>}
          {r.action_summary && <><dt>{t("officer.action_summary")}</dt><dd>{r.action_summary}</dd></>}
          <dt />
          <dd className="muted">{r.officer}</dd>
        </dl>
      ))}
      {canRecord && (
        <div style={{ display: "grid", gap: "0.5rem", marginTop: "0.75rem" }}>
          <p className="small muted">{t("officer.note")}</p>
          {FIELDS.map(([k, type]) => (
            <label key={k} className="field">
              {t(`officer.${k}`)}
              <input type={type} value={values[k] ?? ""} onChange={(e) => setValues({ ...values, [k]: e.target.value })} data-testid={`officer-${k}`} />
            </label>
          ))}
          <label className="field">
            {t("officer.action_summary")}
            <textarea rows={2} value={values.action_summary ?? ""} onChange={(e) => setValues({ ...values, action_summary: e.target.value })} />
          </label>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <button className="btn secondary" onClick={() => void save(false)}>{t("officer.save")}</button>
            <button className="btn" onClick={() => void save(true)} data-testid="officer-record-action">{t("officer.save_action")}</button>
          </div>
        </div>
      )}
      {message && <p className={`banner ${message.kind}`} role="status" style={{ marginTop: "0.6rem" }} data-testid="officer-message">{message.text}</p>}
    </div>
  );
}
