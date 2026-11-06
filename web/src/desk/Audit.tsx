/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api, fmtDateTime } from "../api";
import { useAsync } from "../components/Bits";

export function Audit() {
  const { t, i18n } = useTranslation();
  const month = new Date().toISOString().slice(0, 7);
  const [check, setCheck] = useState<any | null>(null);
  const { data } = useAsync(() => api<{ items: any[] }>("/audit?limit=150"), []);
  const { data: sample } = useAsync(() => api<any>(`/audit/closure-sample?month=${month}&n=5`), [month]);

  return (
    <div className="page">
      <div className="page-head">
        <h1>{t("audit.title")}</h1>
        <button className="btn" onClick={() => api<any>("/audit/verify").then(setCheck)} data-testid="verify-log">{t("audit.verify")}</button>
      </div>
      {check && (
        <p className={`banner ${check.ok ? "info" : "stop"}`} role="status" data-testid="verify-result" style={{ marginBottom: "1rem" }}>
          {check.ok ? t("audit.ok", { n: check.rows_checked }) : t("audit.broken", { id: check.first_bad_id, problem: check.problem })}
        </p>
      )}
      <section className="panel" style={{ marginBottom: "1.25rem" }}>
        <h3>{t("audit.sample")}</h3>
        {sample && sample.sample.length === 0 && <p className="muted small">{t("audit.sample_none")}</p>}
        <ul>
          {sample?.sample.map((s: any) => (
            <li key={s.alert_id}><Link to={`/alerts/${s.alert_id}`}>{s.code}</Link>: {t(`state.${s.closed_as}`)}</li>
          ))}
        </ul>
      </section>
      <table className="grid">
        <thead><tr><th>{t("audit.when")}</th><th>{t("audit.who")}</th><th>{t("audit.what")}</th><th>{t("audit.item")}</th><th>#</th></tr></thead>
        <tbody>
          {data?.items.map((r) => (
            <tr key={r.id}>
              <td>{fmtDateTime(r.at, i18n.language)}</td>
              <td>{r.actor}<div className="small muted">{t(`role.${r.actor_role}`)}</div></td>
              <td>{r.action}{r.details?.to ? `: ${t(`state.${r.details.to}`)}` : ""}</td>
              <td>{r.entity === "alert" ? <Link to={`/alerts/${r.entity_id}`}>{r.entity} {r.entity_id}</Link> : `${r.entity} ${r.entity_id ?? ""}`}</td>
              <td className="small muted" title={r.hash}>{r.id}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
