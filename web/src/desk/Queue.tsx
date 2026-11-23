import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { api, fmtDate, type AlertRow } from "../api";
import { LineSwatch, StatePill, useAsync, usePageTitle } from "../components/Bits";
import { GROUP_COLOUR, GROUP_OF } from "../components/labels";
import { MapView, type Pin } from "../components/MapView";
import { PageState } from "../components/PageState";
import { baseFor, useDataset } from "../dataset";
import { useDemoOnScreen } from "../demo";
import { ScreeningSummary } from "./Screening";

const GROUPS = ["all", "review", "field", "legal", "officer", "watch", "closed", "overdue"] as const;

export function Queue() {
  const { t, i18n } = useTranslation();
  const nav = useNavigate();
  const [group, setGroup] = useState<(typeof GROUPS)[number]>("all");
  const [mode, setMode] = useState("");
  const [cohort, setCohort] = useState("");
  const { dataset } = useDataset();
  const { data, error, status, reload } = useAsync(() => api<{ items: AlertRow[]; has_demo: boolean }>(`/alerts?dataset=${dataset}`), [dataset]);
  useDemoOnScreen(Boolean(data?.has_demo));
  usePageTitle(t("queue.title"));

  const items = useMemo(() => {
    let rows = data?.items ?? [];
    if (group === "overdue") rows = rows.filter((r) => r.overdue);
    else if (group !== "all") rows = rows.filter((r) => GROUP_OF[r.state] === group);
    if (mode) rows = rows.filter((r) => r.mode === mode);
    if (cohort) rows = rows.filter((r) => r.cohort === cohort);
    // Open alerts first, by priority; closed ones after, so they never crowd the top.
    const closed = (r: AlertRow) => (GROUP_OF[r.state] === "closed" ? 1 : 0);
    return [...rows].sort((a, b) => closed(a) - closed(b) || (b.priority_score ?? -1) - (a.priority_score ?? -1));
  }, [data, group, mode, cohort]);

  const pins: Pin[] = useMemo(
    () =>
      items.map((r) => ({
        id: r.id,
        lon: r.lon,
        lat: r.lat,
        colour: r.overdue ? "#c4402f" : GROUP_COLOUR[GROUP_OF[r.state]],
        label: i18n.language === "te" && r.asset_name_te ? r.asset_name_te : r.asset_name,
        big: GROUP_OF[r.state] !== "closed",
        onClick: () => nav(`/alerts/${r.id}`),
      })),
    [items, nav, i18n.language],
  );

  const name = (r: AlertRow) => (i18n.language === "te" && r.asset_name_te ? r.asset_name_te : r.asset_name);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>{t("queue.title")}</h1>
          {/* No count until the alerts have arrived: "0 alerts" while loading reads as an empty queue. */}
          <p className="muted" aria-hidden={!data}>{data ? `${t("queue.count", { count: items.length })}. ${t("queue.sorted")}.` : " "}</p>
        </div>
        <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap", alignItems: "flex-end" }}>
          <label className="field">
            {t("detail.mode")}
            <select value={mode} onChange={(e) => setMode(e.target.value)} data-testid="filter-mode">
              <option value="">{t("group.all")}</option>
              {["ACTION", "VERIFY", "WATCH"].map((m) => <option key={m} value={m}>{t(`mode.${m}`)}</option>)}
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
      <div className="chips" role="group" aria-label="State" style={{ marginBottom: "1rem" }}>
        {GROUPS.map((g) => (
          <button key={g} className="chip" aria-pressed={group === g} onClick={() => setGroup(g)} data-testid={`group-${g}`}>
            {t(`group.${g}`)}
          </button>
        ))}
      </div>
      <PageState error={error} status={status} onRetry={reload} />
      <div className="queue">
        <div className="mapbox">
          <MapView base={baseFor(dataset)} pins={pins} testId="queue-map" />
          <div className="legend">
            {(["review", "field", "legal", "officer", "watch"] as const).map((g) => (
              <span key={g}><i className="pin" style={{ width: 10, height: 10, borderWidth: 2, background: GROUP_COLOUR[g] }} />{t(`group.${g}`)}</span>
            ))}
            <span><i className="pin" style={{ width: 10, height: 10, borderWidth: 2, background: "#c4402f" }} />{t("group.overdue")}</span>
          </div>
        </div>
        <div className="list" data-testid="alert-list">
          <PageState loading={!data && !error} />
          {items.length === 0 && data && <p className="muted" style={{ padding: "1rem" }}>{t(dataset === "real" ? "queue.empty_real" : "queue.empty")}</p>}
          {items.map((r) => (
            <Link key={r.id} to={`/alerts/${r.id}`} className="row" data-testid={`alert-row-${r.code}`}>
              <span className="bar" style={{ background: r.overdue ? "#c4402f" : GROUP_COLOUR[GROUP_OF[r.state]] }} />
              <span>
                <h3>{name(r)}</h3>
                <span className="meta">
                  <StatePill state={r.state} />
                  <span>{t(`change.${r.change_type}`)}</span>
                  <span>{t("queue.acres", { acres: r.area_acres })}</span>
                  {r.zone && <span>{t(r.asset_type === "recovered_parcel" && r.zone === "inside_ftl" ? "zone_parcel.inside_ftl" : `zone.${r.zone}`)}</span>}
                </span>
                <span className="meta">
                  {r.overdue && r.due_at && <span className="flag-overdue">{t("queue.overdue", { date: fmtDate(r.due_at, i18n.language) })}</span>}
                  {!r.overdue && r.due_at && <span>{t("queue.due", { date: fmtDate(r.due_at, i18n.language) })}</span>}
                  {r.owner_name && <span>{t("queue.owner", { name: r.owner_name })}</span>}
                  {r.reopened_count > 0 && <span>{t("queue.reopened")}</span>}
                  {r.flags.includes("permit_conflict") && <span><LineSwatch colour="#b07219" /> {t("detail.permits")}</span>}
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
