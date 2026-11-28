/* eslint-disable @typescript-eslint/no-explicit-any */
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { API_BASE, api, authHeaders, fmtDate } from "../api";
import { useAsync, usePageTitle } from "../components/Bits";
import { PageState } from "../components/PageState";
import { Segmented } from "../components/Segmented";
import { Printer } from "lucide-react";
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

const FIGURES = ["watched", "new_alerts", "reviewed", "confirmed", "waiting"] as const;

/** Section 9.4: one page a month for the officials, from the database only (incidents since D-057). */
export function Monthly() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const choices = useMemo(() => months(4), []);
  const [month, setMonth] = useState(choices[0]);
  const { data, error, status, loading, reload } = useAsync(() => api<any>(`/bulletins/${month}`), [month]);
  usePageTitle(t("monthly.title", { month: monthName(month, lang) }));

  const print = async () => {
    const res = await fetch(`${API_BASE}/bulletins/${month}/pdf`, { headers: authHeaders() });
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
        <div className="head-actions">
          <Segmented label={t("monthly.choose")} value={month} onChange={setMonth} options={choices.map((m) => ({ value: m, label: monthName(m, lang) }))} />
          <button className="btn secondary" onClick={() => void print()} data-testid="print-monthly"><Printer aria-hidden="true" />{t("monthly.print")}</button>
        </div>
      </div>
      <PageState loading={loading && !data} error={error} status={status} onRetry={reload} />
      {data && !error && (
        <>
          <div className="figures">
            {FIGURES.map((k) => (
              <div key={k} className={`figure ${k === "waiting" && data.counts.waiting > 0 ? "late" : ""}`} data-testid={`figure-${k}`}>
                <b>{data.counts[k]}</b>
                <span>{t(`monthly.${k}`, { days: data.wait_days })}</span>
                <small>{t(k === "waiting" ? "monthly.was_end" : "monthly.was", { n: data.last_month.counts[k], month: monthName(data.last_month.month, lang) })}</small>
              </div>
            ))}
          </div>
          <div className="monthly-grid">
            <figure className="monthly-map">
              <div dangerouslySetInnerHTML={{ __html: data.map_svg }} />
              <figcaption className="monthly-legend" aria-label={t("monthly.map_legend_label")}>
                <span><i className="legend-swatch lake" />{t("monthly.legend_water")}</span>
                <span><i className="legend-swatch land" />{t("monthly.legend_land")}</span>
                <span><i className="legend-swatch incident" />{t("monthly.legend_new")}</span>
                <span><i className="legend-swatch waiting" />{t("monthly.legend_waiting", { days: data.wait_days })}</span>
              </figcaption>
            </figure>
            <div>
              <h2>{t("monthly.what_changed")}</h2>
              {Object.keys(data.change_types).length === 0 && <p className="muted">{t("monthly.no_new")}</p>}
              <ul className="who-list" data-testid="change-types">
                {Object.entries(data.change_types).map(([k, n]) => <li key={k}><span>{t(`change.${k}`)}</span><b>{n as number}</b></li>)}
              </ul>
              <h2 className="monthly-sub">{t("monthly.list", { days: data.wait_days })}</h2>
              {data.waiting.length === 0 && <p className="muted">{t("monthly.none", { days: data.wait_days })}</p>}
              <ul className="overdue-list" data-testid="waiting-list">
                {data.waiting.map((o: any) => (
                  <li key={o.alert_id}>
                    <Link to={`/alerts/${o.alert_id}`}>{o.asset_name}</Link>
                    <span className="small muted">{o.code}, {t(`state.${o.state}`)}</span>
                    <b className="flag-overdue">{t("monthly.days_waiting", { n: o.days_waiting })}</b>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <p className="small muted section">{t("monthly.source")}</p>
        </>
      )}
    </div>
  );
}
