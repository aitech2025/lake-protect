/* eslint-disable @typescript-eslint/no-explicit-any */
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { X } from "lucide-react";
import { api, fmtDate, type AlertRow } from "../api";
import { AREA_LEVELS, AreaFilter, NO_AREA, useAreaParams, type Placed } from "../components/AreaFilter";
import { StatePill, useAsync, usePageTitle } from "../components/Bits";
import { isFieldOfficer, useAuth } from "../auth";
import { CHANGE_TYPES, GROUP_COLOUR, GROUP_OF, STATES } from "../components/labels";
import { MapView, type Pin } from "../components/MapView";
import { PageState } from "../components/PageState";
import { Segmented } from "../components/Segmented";
import { ScreeningSummary } from "./Screening";

type Filter = "active" | "all" | (typeof STATES)[number];
const FILTERS: Filter[] = ["active", ...STATES, "all"];

/** Incidents (D-057): every change the weekly screen found, and where each one stands. */
export function Queue() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const field = isFieldOfficer(user);
  const title = field ? t("nav.field_visits") : t("queue.title");
  const nav = useNavigate();
  // The dashboard opens this list with its area and rule in the address (D-060): the server applies
  // them, and the state chips start at "all" so they hide nothing the number counted.
  const [params, setParams] = useSearchParams();
  const linked = ["district", "mandal", "village", "state", "waiting", "week", "asset_id"].filter((k) => params.get(k) !== null);
  const linkedQuery = linked.map((k) => `&${k}=${encodeURIComponent(params.get(k) ?? "")}`).join("");
  // The area is also what the District, Mandal and Village pickers show and set (D-069); the banner
  // lists only the overview's other rules.
  const rules = linked.filter((k) => !(AREA_LEVELS as readonly string[]).includes(k));
  const [area, setArea] = useAreaParams();
  const [filter, setFilter] = useState<Filter>(linked.length ? "all" : "active");
  const [change, setChange] = useState("");
  const [cohort, setCohort] = useState("");
  const [landTab, setLandTab] = useState<"all" | "lakes" | "lands">("all");
  const areas = useAsync(() => api<{ features: any[] }>("/assets"), []);
  const { data, error, status, reload } = useAsync(() => api<{ items: AlertRow[] }>(`/alerts${linkedQuery.replace(/^&/, "?")}`), [linkedQuery]);
  usePageTitle(title);

  // The API applies the area; the page narrows by the rest.
  const items = useMemo(() => {
    let rows = data?.items ?? [];
    rows = rows.filter((r) => landTab === "all" || (landTab === "lakes" ? r.asset_type === "lake" : r.asset_type !== "lake"));
    if (filter === "active") rows = rows.filter((r) => r.state !== "CLOSED");
    else if (filter !== "all") rows = rows.filter((r) => r.state === filter);
    if (change) rows = rows.filter((r) => (change === "building" ? ["building", "small_structure"].includes(r.change_type) : r.change_type === change));
    if (cohort) rows = rows.filter((r) => r.cohort === cohort);
    return rows;
  }, [data, filter, change, cohort, landTab]);

  // The areas offered: those of the locations this person can see, of the chosen kind of land.
  const places: Placed[] = useMemo(
    () => (areas.data?.features ?? [])
      .filter((a) => landTab === "all" || (landTab === "lakes" ? a.properties.category === "water_body" : a.properties.category !== "water_body"))
      .map((a) => a.properties),
    [areas.data, landTab],
  );
  const narrowed = !!(change || cohort || area.district || area.mandal || area.village || landTab !== "all");

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
  const clearNarrowing = () => { setChange(""); setCohort(""); setArea(NO_AREA); setLandTab("all"); };
  const clearRules = () => {
    setParams((prev) => {
      const q = new URLSearchParams(prev);
      rules.forEach((k) => q.delete(k));
      return q;
    });
    setFilter("active");
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>{title}</h1>
          <p className="muted" aria-hidden={!data}>{data ? (field ? t("queue.field_lede", { count: items.length }) : `${t("queue.count", { count: items.length })}. ${t("queue.sorted")}.`) : " "}</p>
        </div>
      </div>
      {rules.length > 0 && (
        <p className="banner info linked-filter" data-testid="linked-filter">
          {t("queue.linked")}{" "}
          {rules.map((k, i) => (
            <b key={k}>{i > 0 ? ", " : ""}{k === "waiting" ? t("dashboard.figure.waiting") : k === "state" ? (params.get(k) ?? "").split(",").map((x) => t(`state.${x}`)).join(", ") : k === "week" ? t("queue.linked_week", { week: params.get(k) }) : t("queue.linked_asset")}</b>
          ))}
          <button className="btn quiet" onClick={clearRules} data-testid="linked-clear">{t("queue.linked_clear")}</button>
        </p>
      )}
      {!field && <ScreeningSummary />}
      <div className="toolbar" role="search" aria-label={t("queue.filters")}>
        <div className="toolbar-row">
          <Segmented
            label={t("queue.state")}
            value={filter}
            onChange={setFilter}
            options={FILTERS.map((f) => ({ value: f, testId: `group-${f}`, label: f === "active" ? t("group.active") : f === "all" ? t("group.all") : t(`state.${f}`) }))}
          />
          <Segmented
            label={t("queue.land_group")}
            className="incident-tabs"
            value={landTab}
            onChange={setLandTab}
            options={(["all", "lakes", "lands"] as const).map((k) => ({ value: k, label: t(k === "all" ? "group.all" : `assets.tab.${k}`) }))}
          />
        </div>
        <div className="toolbar-row">
          <AreaFilter places={places} value={area} onChange={setArea} testId="incident-area" />
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
          {narrowed && <button type="button" className="btn secondary sm" onClick={clearNarrowing}><X aria-hidden="true" />{t("queue.clear_filters")}</button>}
        </div>
      </div>
      <PageState error={error} status={status} onRetry={reload} />
      <div className="queue">
        <div className="list" data-testid="alert-list">
          <PageState loading={!data && !error} />
          {items.length === 0 && data && <p className="list-empty">{field ? t("queue.field_empty") : t("queue.empty_real")}</p>}
          {items.map((r) => (
            <Link key={r.id} to={`/alerts/${r.id}`} className="row" data-testid={`alert-row-${r.code}`}>
              <span className="bar" style={{ background: GROUP_COLOUR[GROUP_OF[r.state]] }} />
              <span>
                <h3>{name(r)}</h3>
                <span className="meta">
                  <StatePill state={r.state} />
                  <b className="change-type">{t(`change.${r.change_type}`)}</b>
                  {r.origin === "citizen" && <span className="pill field" data-testid="origin-citizen">{t("queue.citizen")}</span>}
                  {r.field_officer && r.state === "FIELD_VISIT" && <span>{t("case.assigned_to", { name: r.field_officer })}</span>}
                  <span>{t("queue.acres", { acres: r.area_acres })}</span>
                  {zone(r) && <span>{zone(r)}</span>}
                </span>
                <span className="meta">
                  <span>{t("queue.first_seen", { date: fmtDate(r.first_changed_at, i18n.language) })}</span>
                  {r.review_count > 0 && <span>{t("queue.reviews", { count: r.review_count })}</span>}
                  {(r.citizen_reports ?? 0) > 0 && r.origin !== "citizen" && <span>{t("queue.citizen_reports", { count: r.citizen_reports })}</span>}
                  {r.resolution && <span>{t(`resolution.${r.resolution}`)}</span>}
                  {r.court_matter && <span className="flag-overdue">{t("queue.court")}</span>}
                  {!r.boundary_confirmed && <span className="flag">{t("queue.boundary_unconfirmed")}</span>}
                  {r.permit_conflict && <span className="flag">{t("detail.permits")}</span>}
                  {r.related_alert_id && <span>{t("queue.seen_again")}</span>}
                  <span className="mono">{r.code}</span>
                </span>
              </span>
              <span className="score">
                <b>{r.priority_score !== null ? Math.round(r.priority_score) : "–"}</b>
                {t("queue.priority", { score: "" }).trim()}
              </span>
            </Link>
          ))}
        </div>
        <div className="mapbox">
          <MapView pins={pins} testId="queue-map" />
          <div className="legend">
            {STATES.map((s) => (
              <span key={s}><i className="pin" style={{ background: GROUP_COLOUR[GROUP_OF[s]] }} />{t(`state.${s}`)}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
