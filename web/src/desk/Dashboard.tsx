import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, type DashRow, type Figures, type Overview, type Tone } from "../api";
import { isAdmin, useAuth } from "../auth";
import { useAsync, usePageTitle } from "../components/Bits";
import { MapView, type Pin } from "../components/MapView";
import { PageState, TableRegion } from "../components/PageState";
import { baseFor, useDataset } from "../dataset";
import { useDemoOnScreen } from "../demo";
import "./dashboard.css";

const LEVELS = ["district", "mandal", "village"] as const;

/** Status colours (reserved: never used for anything else on this page), each shown with a label and a mark. */
export const TONE: Record<Tone, { colour: string; mark: string }> = {
  waiting: { colour: "#b8392a", mark: "!" },
  open: { colour: "#b07219", mark: "●" },
  changed: { colour: "#1f6fa8", mark: "◆" },
  no_look: { colour: "#75848b", mark: "○" },
  quiet: { colour: "#2d7a57", mark: "✓" },
};

function query(params: Record<string, string | undefined>): string {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => v !== undefined && v !== "" && q.set(k, v));
  const s = q.toString();
  return s ? `?${s}` : "";
}

/** The incident list behind a number: the same area, and the same rule the number was counted with. */
function incidentsLink(area: Record<string, string>, rule: Record<string, string>): string {
  return `/alerts${query({ ...area, ...rule })}`;
}

export function Dashboard() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const { user } = useAuth();
  const { dataset } = useDataset();
  const nav = useNavigate();
  const [params, setParams] = useSearchParams();
  const area: Record<string, string> = {};
  LEVELS.forEach((k) => {
    const v = params.get(k);
    if (v !== null) area[k] = v;
  });
  const key = query(area);
  const { data, error, status, loading, reload } = useAsync(() => api<Overview>(`/dashboard${query({ dataset, ...area })}`), [dataset, key]);
  useDemoOnScreen(dataset === "demo" && Boolean(data));
  usePageTitle(t("dashboard.title"));

  const go = (p: Record<string, string>) => setParams(p);
  const areaName = (name: string) => (name === "-" ? t("dashboard.not_recorded") : name);
  const pins: Pin[] = useMemo(
    () =>
      (data?.pins ?? []).map((p) => ({
        id: p.asset_id,
        lon: p.lon,
        lat: p.lat,
        colour: TONE[p.tone].colour,
        label: `${lang === "te" && p.name_te ? p.name_te : p.name}: ${t(`dashboard.tone.${p.tone}`)}`,
        // Only the places waiting longest carry a name on the map; the legend explains the colours.
        big: p.tone === "waiting",
        onClick: () => nav(`/assets?asset=${p.asset_id}`),
      })),
    [data, lang, nav, t],
  );

  const f = data?.figures;
  return (
    <div className="page dashboard" data-testid="dashboard">
      <div className="page-head">
        <div>
          <h1>{t("dashboard.title")}</h1>
          <p className="muted">{data ? (data.week ? t("dashboard.lede", { week: data.week }) : t("dashboard.no_week")) : " "}</p>
        </div>
        {data && !isAdmin(user) && data.my_areas.length > 0 && (
          <div className="chips" role="group" aria-label={t("dashboard.my_area")}>
            <span className="small muted">{t("dashboard.my_area")}</span>
            {data.my_areas.map((a) => {
              const p: Record<string, string> = a.mandal ? { district: a.district, mandal: a.mandal } : { district: a.district };
              return (
                <button key={`${a.district}/${a.mandal}`} className="chip" aria-pressed={query(p) === key} onClick={() => go(p)} data-testid="my-area">
                  {a.mandal ? `${a.mandal}, ${a.district}` : a.district}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {data && (
        <nav className="crumbs drill" aria-label={t("dashboard.path")} data-testid="dash-path">
          {data.path.map((p, i) => (
            <span key={p.level}>
              {i > 0 && <span aria-hidden="true"> › </span>}
              {i === data.path.length - 1 ? <b aria-current="page">{areaName(p.name)}</b> : <button className="btn quiet" onClick={() => go(p.params)}>{areaName(p.name)}</button>}
            </span>
          ))}
        </nav>
      )}
      <PageState loading={loading && !data} error={error} status={status} onRetry={reload} />
      {data && f && !error && (
        <>
          <FigureRow f={f} area={data.filters} week={data.week} />
          <p className="small by-kind" data-testid="by-category">
            <b>{t("dashboard.by_category")}:</b>{" "}
            {data.by_category.map((c) => `${lang === "te" ? c.label.te : c.label.en} ${c.status === "live" ? c.watched : `(${t("dashboard.planned")})`}`).join(" · ")}
          </p>
          {data.area_source && <p className="small muted" style={{ marginBottom: "0.75rem" }}>{t("dashboard.area_source")}</p>}
          <div className="dash-grid">
            <div className="mapbox" style={{ height: 360 }}>
              <MapView base={baseFor(dataset)} pins={pins} testId="dashboard-map" />
              <div className="legend">
                {(Object.keys(TONE) as Tone[]).map((k) => (
                  <span key={k}><i className="pin" style={{ width: 10, height: 10, borderWidth: 2, background: TONE[k].colour }} />{t(`dashboard.tone.${k}`)}</span>
                ))}
              </div>
            </div>
            <Trend data={data} />
          </div>
          <Children data={data} onOpen={(row) => (row.kind === "asset" ? nav(`/assets?asset=${row.asset_id}`) : go(row.params))} />
        </>
      )}
    </div>
  );
}

function FigureRow({ f, area, week }: { f: Figures; area: Record<string, string>; week: string | null }) {
  const { t } = useTranslation();
  const ack = f.ack_considered ? Math.round((100 * f.ack_on_time) / f.ack_considered) : null;
  const tiles: { k: string; n: number | string; to?: string; tone?: Tone; small?: string }[] = [
    { k: "assets", n: f.assets, small: t("dashboard.boundary", { n: f.boundary_confirmed, total: f.assets }) },
    { k: "clear_look", n: f.clear_look, small: f.no_clear_look ? t("dashboard.no_clear_look", { n: f.no_clear_look }) : undefined },
    { k: "changed", n: f.changed },
    { k: "new_incidents", n: f.new_incidents, to: week ? incidentsLink(area, { week }) : undefined },
    { k: "open", n: f.open, to: incidentsLink(area, { state: "OPEN" }), tone: f.open ? "open" : undefined },
    { k: "under_review", n: f.under_review, to: incidentsLink(area, { state: "UNDER_REVIEW" }) },
    { k: "waiting", n: f.waiting, to: incidentsLink(area, { waiting: "true" }), tone: f.waiting ? "waiting" : undefined },
    { k: "confirmed", n: f.confirmed, to: incidentsLink(area, { state: "CONFIRMED" }) },
    { k: "ack", n: ack === null ? "–" : `${ack}%`, small: ack === null ? t("dashboard.ack_none") : t("dashboard.ack_of", { n: f.ack_on_time, total: f.ack_considered }) },
  ];
  return (
    <div className="dash-figures" data-testid="dash-figures">
      {tiles.map((x) => {
        const body = (
          <>
            <b>{x.tone && <span className="tone-mark" style={{ color: TONE[x.tone].colour }} aria-hidden="true">{TONE[x.tone].mark} </span>}{x.n}</b>
            <span>{t(`dashboard.figure.${x.k}`)}</span>
            {x.small && <small>{x.small}</small>}
          </>
        );
        return x.to ? (
          <Link key={x.k} to={x.to} className="dash-figure link" data-testid={`fig-${x.k}`}>{body}</Link>
        ) : (
          <div key={x.k} className="dash-figure" data-testid={`fig-${x.k}`}>{body}</div>
        );
      })}
    </div>
  );
}

/** Two single-series bar charts of the last weeks: one measure each, one axis each. */
function Trend({ data }: { data: Overview }) {
  const { t } = useTranslation();
  const series = [
    { k: "changed" as const, colour: "#1f6fa8" },
    { k: "new_incidents" as const, colour: "#1f6fa8" },
  ];
  return (
    <div className="panel trend" data-testid="trend">
      <h2 className="title-s">{t("dashboard.trend_title")}</h2>
      {data.trend.length === 0 ? (
        <p className="muted small">{t("dashboard.no_week")}</p>
      ) : (
        <>
          {series.map((s) => <Bars key={s.k} title={t(`dashboard.trend.${s.k}`)} colour={s.colour} rows={data.trend.map((w) => ({ week: w.week, n: w[s.k] }))} />)}
          <details className="small">
            <summary>{t("dashboard.as_table")}</summary>
            <table className="grid" style={{ marginTop: "0.5rem" }}>
              <thead>
                <tr><th>{t("dashboard.col.week")}</th><th>{t("dashboard.trend.changed")}</th><th>{t("dashboard.trend.new_incidents")}</th><th>{t("dashboard.figure.clear_look")}</th></tr>
              </thead>
              <tbody>
                {data.trend.map((w) => <tr key={w.week}><td>{w.week}</td><td>{w.changed}</td><td>{w.new_incidents}</td><td>{w.clear_look}</td></tr>)}
              </tbody>
            </table>
          </details>
        </>
      )}
    </div>
  );
}

function Bars({ title, colour, rows }: { title: string; colour: string; rows: { week: string; n: number }[] }) {
  const [hover, setHover] = useState<number | null>(null);
  const W = 300, H = 96, top = 14, bottom = 18;
  const max = Math.max(1, ...rows.map((r) => r.n));
  const slot = W / rows.length;
  const bw = Math.min(22, slot - 2);
  const shown = hover ?? rows.length - 1;
  return (
    <figure className="bars">
      <figcaption>
        <span>{title}</span>
        <span className="small muted" aria-live="polite">{rows[shown].week}: <b>{rows[shown].n}</b></span>
      </figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={`${title}: ${rows.map((r) => `${r.week} ${r.n}`).join(", ")}`} onMouseLeave={() => setHover(null)}>
        <line x1="0" x2={W} y1={H - bottom} y2={H - bottom} stroke="#d3dad4" />
        <text x="0" y="10" fontSize="9" fill="#75848b">{max}</text>
        {rows.map((r, i) => {
          const h = ((H - top - bottom) * r.n) / max;
          const x = i * slot + (slot - bw) / 2;
          const y = H - bottom - h;
          const rr = Math.min(4, h / 2, bw / 2);
          // A bar with rounded top corners only, anchored to the baseline.
          const d = h > 0 ? `M${x},${H - bottom} V${y + rr} Q${x},${y} ${x + rr},${y} H${x + bw - rr} Q${x + bw},${y} ${x + bw},${y + rr} V${H - bottom} Z` : "";
          return (
            <g key={r.week} onMouseEnter={() => setHover(i)} onFocus={() => setHover(i)} tabIndex={0} aria-label={`${r.week}: ${r.n}`}>
              <rect x={i * slot} y={0} width={slot} height={H} fill="transparent" />
              {d && <path d={d} fill={colour} opacity={hover === null || hover === i ? 1 : 0.55} />}
              <text x={i * slot + slot / 2} y={H - 4} fontSize="9" textAnchor="middle" fill="#75848b">{r.week.slice(-3)}</text>
            </g>
          );
        })}
      </svg>
    </figure>
  );
}

function Children({ data, onOpen }: { data: Overview; onOpen: (row: DashRow) => void }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const cols: { k: keyof Figures; rule?: Record<string, string> }[] = [
    { k: "assets" },
    { k: "clear_look" },
    { k: "changed" },
    { k: "new_incidents", rule: data.week ? { week: data.week } : undefined },
    { k: "open", rule: { state: "OPEN" } },
    { k: "under_review", rule: { state: "UNDER_REVIEW" } },
    { k: "waiting", rule: { waiting: "true" } },
    { k: "confirmed", rule: { state: "CONFIRMED" } },
  ];
  if (data.children.length === 0) return <p className="muted">{t("dashboard.empty")}</p>;
  return (
    <section style={{ marginTop: "1.25rem" }}>
      <h2 className="title-s" style={{ marginBottom: "0.5rem" }}>{t(`dashboard.by.${data.child_level}`)}</h2>
      <TableRegion label={t(`dashboard.by.${data.child_level}`)}>
        <table className="grid dash-table" data-testid="dash-children">
          <thead>
            <tr>
              <th>{t(`dashboard.level.${data.child_level}`)}</th>
              <th>{t("dashboard.col.status")}</th>
              {cols.map((c) => <th key={c.k} className="num">{t(`dashboard.col.${c.k}`)}</th>)}
            </tr>
          </thead>
          <tbody>
            {data.children.map((row) => {
              const name = row.kind === "asset" ? (lang === "te" && row.name_te ? row.name_te : row.name) : row.name === "-" ? t("dashboard.not_recorded") : row.name;
              return (
                <tr key={`${row.kind}-${row.asset_id ?? row.name}`} data-testid={`dash-row-${row.name}`}>
                  <td>
                    <button className="btn quiet" onClick={() => onOpen(row)}>{name}</button>
                    {row.kind === "asset" && row.week_status && <div className="small muted">{t(`weeks.status.${row.week_status}`)}</div>}
                    {row.kind === "asset" && row.monitored === false && <div className="small flag">{t("dashboard.not_watched")}</div>}
                  </td>
                  <td><span className="tone" style={{ borderColor: TONE[row.tone].colour }}><i style={{ color: TONE[row.tone].colour }} aria-hidden="true">{TONE[row.tone].mark}</i>{t(`dashboard.tone.${row.tone}`)}</span></td>
                  {cols.map((c) => {
                    const n = row.figures[c.k];
                    const to = c.rule && n > 0 ? incidentsLink(row.kind === "asset" ? { asset_id: String(row.asset_id) } : row.params, c.rule) : null;
                    return <td key={c.k} className="num">{to ? <Link to={to} data-testid={`dash-${row.name}-${c.k}`}>{n}</Link> : n}</td>;
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </TableRegion>
    </section>
  );
}
