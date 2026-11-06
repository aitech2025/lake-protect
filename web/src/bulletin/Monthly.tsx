/* eslint-disable @typescript-eslint/no-explicit-any */
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { API_BASE, api, authHeaders, fmtDate } from "../api";
import { useAsync } from "../components/Bits";
import { useDemoOnScreen } from "../demo";
import "./monthly.css";

function months(n: number): string[] {
  const out: string[] = [];
  const d = new Date();
  for (let i = 0; i < n; i++) {
    const m = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() - i, 1));
    out.push(m.toISOString().slice(0, 7));
  }
  return out;
}

function monthName(month: string, lang: string): string {
  return new Date(month + "-01T00:00:00Z").toLocaleDateString(lang === "te" ? "te-IN" : "en-IN", { month: "long", year: "numeric", timeZone: "UTC" });
}

const FIGURES = ["watched", "new_alerts", "verified", "action_taken", "overdue"] as const;

/** Section 9.4: one page a month for senior officers, from the database only. */
export function Monthly() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const choices = useMemo(() => months(4), []);
  const [month, setMonth] = useState(choices[0]);
  const [dataset, setDataset] = useState<"demo" | "real">("demo");
  const { data, error } = useAsync(() => api<any>(`/bulletins/${month}?dataset=${dataset}`), [month, dataset]);
  useDemoOnScreen(dataset === "demo" && Boolean(data));

  const print = async () => {
    const res = await fetch(`${API_BASE}/bulletins/${month}/pdf?dataset=${dataset}`, { headers: authHeaders() });
    const url = URL.createObjectURL(await res.blob());
    const a = document.createElement("a");
    a.href = url;
    a.target = "_blank";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  };

  return (
    <div className="page monthly" data-testid="monthly">
      <div className="page-head">
        <div>
          <h1>{t("monthly.title", { month: monthName(month, lang) })}</h1>
          {data && (
            <p className="muted">
              {data.complete_month ? t("monthly.whole") : t("monthly.to_date", { date: fmtDate(data.as_of, lang) })}{" "}
              {t("monthly.compared", { month: monthName(data.last_month.month, lang) })}
            </p>
          )}
        </div>
        <button className="btn" onClick={() => void print()} data-testid="print-monthly">{t("monthly.print")}</button>
      </div>
      <div className="chips" style={{ marginBottom: "1.25rem" }}>
        {choices.map((m) => <button key={m} className="chip" aria-pressed={m === month} onClick={() => setMonth(m)}>{monthName(m, lang)}</button>)}
        <span style={{ width: "1rem" }} />
        <button className="chip" aria-pressed={dataset === "demo"} onClick={() => setDataset("demo")}>{t("monthly.dataset_demo")}</button>
        <button className="chip" aria-pressed={dataset === "real"} onClick={() => setDataset("real")}>{t("monthly.dataset_real")}</button>
      </div>
      {error && <p className="error">{t("error.load", { msg: error })}</p>}
      {data && (
        <>
          <div className="figures">
            {FIGURES.map((k) => (
              <div key={k} className={`figure ${k === "overdue" && data.counts.overdue > 0 ? "late" : ""}`} data-testid={`figure-${k}`}>
                <b>{data.counts[k]}</b>
                <span>{t(`monthly.${k}`)}</span>
                <small>{t(k === "overdue" ? "monthly.was_end" : "monthly.was", { n: data.last_month.counts[k], month: monthName(data.last_month.month, lang) })}</small>
              </div>
            ))}
          </div>
          <div className="monthly-grid">
            <figure className="monthly-map">
              <div dangerouslySetInnerHTML={{ __html: data.map_svg }} />
              <figcaption className="small muted">{t("monthly.map_legend")}</figcaption>
            </figure>
            <div>
              <h2>{t("monthly.by_who")}</h2>
              {data.overdue_by_responsible.length === 0 && <p className="muted">{t("monthly.none")}</p>}
              <ul className="who-list">
                {data.overdue_by_responsible.map((r: any) => <li key={r.responsible}><span>{r.responsible}</span><b>{r.count}</b></li>)}
              </ul>
              <h2 style={{ marginTop: "1.5rem" }}>{t("monthly.list")}</h2>
              <ul className="overdue-list" data-testid="overdue-list">
                {data.overdue.map((o: any) => (
                  <li key={o.alert_id}>
                    <Link to={`/alerts/${o.alert_id}`}>{o.asset_name}</Link>
                    <span className="small muted">{o.code}, {t(`state.${o.state}`)}, {o.responsible}</span>
                    <b className="flag-overdue">{t("monthly.days_late", { n: o.days_overdue })}</b>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <p className="small muted" style={{ marginTop: "1.5rem" }}>{t("monthly.source")}</p>
        </>
      )}
    </div>
  );
}
