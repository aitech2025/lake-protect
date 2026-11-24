import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { api, fmtDate, type AlertRow } from "../api";
import { StatePill, useAsync, usePageTitle } from "../components/Bits";
import { CHANGE_TYPES, GROUP_COLOUR, GROUP_OF, STATES } from "../components/labels";
import { MapView, type Pin } from "../components/MapView";
import { PageState } from "../components/PageState";
import { baseFor, useDataset } from "../dataset";
import { useDemoOnScreen } from "../demo";
import { ScreeningSummary } from "./Screening";

type Filter = "active" | "all" | (typeof STATES)[number];
const FILTERS: Filter[] = ["active", ...STATES, "all"];

/** Incidents (D-057): every change the weekly screen found, and where each one stands. */
export function Queue() {
  const { t, i18n } = useTranslation();
  const nav = useNavigate();
  const [filter, setFilter] = useState<Filter>("active");
  const [change, setChange] = useState("");
  const [cohort, setCohort] = useState("");
  const { dataset } = useDataset();
  const { data, error, status, reload } = useAsync(() => api<{ items: AlertRow[]; has_demo: boolean }>(`/alerts?dataset=${dataset}`), [dataset]);
  useDemoOnScreen(Boolean(data?.has_demo));
  usePageTitle(t("queue.title"));

  const items = useMemo(() => {
    let rows = data?.items ?? [];
    if (filter === "active") rows = rows.filter((r) => r.state !== "CLOSED");
    else if (filter !== "all") rows = rows.filter((r) => r.state === filter);
    if (change) rows = rows.filter((r) => (change === "building" ? ["building", "small_structure"].includes(r.change_type) : r.change_type === change));
    if (cohort) rows = rows.filter((r) => r.cohort === cohort);
    return rows;
  }, [data, filter, change, cohort]);

  const pins: Pin[] = useMemo(
    () =>
      items.map((r) => ({
        id: r.id,
        lon: r.lon,
        lat: r.lat,
        colour: GROUP_COLOUR[GROUP_OF[r.state]],
        label: i18n.language === "te" && r.asset_name_te ? r.asset_name_te : r.asset_name,
        big: r.state !== "CLOSED",
        onClick: () => nav(`/alerts/${r.id}`),
      })),
    [items, nav, i18n.language],
  );
  const name = (r: AlertRow) => (i18n.language === "te" && r.asset_name_te ? r.asset_name_te : r.asset_name);
  const zone = (r: AlertRow) => (r.zone ? t(r.asset_type === "recovered_parcel" && r.zone === "inside_ftl" ? "zone_parcel.inside_ftl" : `zone.${r.zone}`) : "");

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>{t("queue.title")}</h1>
          <p className="muted" aria-hidden={!data}>{data ? `${t("queue.count", { count: items.length })}. ${t("queue.sorted")}.` : " "}</p>
        </div>
        <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap", alignItems: "flex-end" }}>
          <label className="field">
            {t("queue.what_changed")}
            <select value={change} onChange={(e) => setChange(e.target.value)} data-testid="filter-change">
              <option value="">{t("group.all")}</option>
              {CHANGE_TYPES.map((c) => <option key={c} value={c}>{t(`change.${c}`)}</option>)}
            </select>
          </label>
          <label className="field">
            {t("queue.cohort")}
            <select value={cohort} onChange={(e) => setCohort(e.target.value)} data-testid="filter-cohort">
              <option value="">{t("group.all")}</option>
              {["A_RECOVERED", "B_FINAL", "C_PRELIM", "D_UNNOTIFIED"].map((c) => <option key={c} value={c}>{t(`cohort.${c}`)}</option>)}
            </select>
          </label>
        </div>
      </div>
      {dataset === "real" && <ScreeningSummary />}
      <div className="chips" role="group" aria-label={t("queue.state")} style={{ marginBottom: "1rem" }}>
        {FILTERS.map((f) => (
          <button key={f} className="chip" aria-pressed={filter === f} onClick={() => setFilter(f)} data-testid={`group-${f}`}>
            {f === "active" ? t("group.active") : f === "all" ? t("group.all") : t(`state.${f}`)}
          </button>
        ))}
      </div>
      <PageState error={error} status={status} onRetry={reload} />
      <div className="queue">
        <div className="mapbox">
          <MapView base={baseFor(dataset)} pins={pins} testId="queue-map" />
          <div className="legend">
            {STATES.map((s) => (
              <span key={s}><i className="pin" style={{ width: 10, height: 10, borderWidth: 2, background: GROUP_COLOUR[GROUP_OF[s]] }} />{t(`state.${s}`)}</span>
            ))}
          </div>
        </div>
        <div className="list" data-testid="alert-list">
          <PageState loading={!data && !error} />
          {items.length === 0 && data && <p className="muted" style={{ padding: "1rem" }}>{t(dataset === "real" ? "queue.empty_real" : "queue.empty")}</p>}
          {items.map((r) => (
            <Link key={r.id} to={`/alerts/${r.id}`} className="row" data-testid={`alert-row-${r.code}`}>
              <span className="bar" style={{ background: GROUP_COLOUR[GROUP_OF[r.state]] }} />
              <span>
                <h3>{name(r)}</h3>
                <span className="meta">
                  <StatePill state={r.state} />
                  <b className="change-type">{t(`change.${r.change_type}`)}</b>
                  <span>{t("queue.acres", { acres: r.area_acres })}</span>
                  {zone(r) && <span>{zone(r)}</span>}
                  <span>{t("queue.first_seen", { date: fmtDate(r.first_changed_at, i18n.language) })}</span>
                </span>
                <span className="meta">
                  {r.review_count > 0 && <span>{t("queue.reviews", { count: r.review_count })}</span>}
                  {r.resolution && <span>{t(`resolution.${r.resolution}`)}</span>}
                  {r.court_matter && <span className="flag-overdue">{t("queue.court")}</span>}
                  {!r.boundary_confirmed && <span className="flag">{t("queue.boundary_unconfirmed")}</span>}
                  {r.permit_conflict && <span className="flag">{t("detail.permits")}</span>}
                  {r.related_alert_id && <span>{t("queue.seen_again")}</span>}
                  <span className="small">{r.code}</span>
                </span>
              </span>
              <span className="score">
                <b>{r.priority_score !== null ? Math.round(r.priority_score) : "–"}</b>
                {t("queue.priority", { score: "" }).trim()}
              </span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
