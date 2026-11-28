import { useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, ChevronRight } from "lucide-react";
import { api, type DashRow, type Figures, type Overview, type Tone } from "../api";
import { isAdmin, useAuth } from "../auth";
import { useAsync, usePageTitle } from "../components/Bits";
import { MapView, type Pin } from "../components/MapView";
import { PageState, TableRegion } from "../components/PageState";
import "./dashboard.css";

const LEVELS = ["district", "mandal", "village"] as const;

/** Status colours (reserved: never used for anything else on this page), each shown with a label and a mark. */
export const TONE: Record<Tone, { colour: string; mark: string }> = {
  waiting: { colour: "#c94b4b", mark: "!" },
  open: { colour: "#d69b32", mark: "!" },
  changed: { colour: "#167c80", mark: "+" },
  no_look: { colour: "#7b8794", mark: "–" },
  quiet: { colour: "#27845a", mark: "✓" },
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
  const nav = useNavigate();
  const [params, setParams] = useSearchParams();
  const area: Record<string, string> = {};
  LEVELS.forEach((k) => {
    const v = params.get(k);
    if (v !== null) area[k] = v;
  });
  const key = query(area);
  const { data, error, status, loading, reload } = useAsync(() => api<Overview>(`/dashboard${query(area)}`), [key]);
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
        onClick: () => nav(`/assets/${p.asset_id}`),
      })),
    [data, lang, nav, t],
  );

  // The map fits its locations clear of the legend and the note drawn over it.
  const legendRef = useRef<HTMLDivElement>(null);
  const noteRef = useRef<HTMLParagraphElement>(null);
  const mapPanels = useMemo(() => [legendRef, noteRef], []);

  const f = data?.figures;
  const parent: { to: Record<string, string>; label: string } | null =
    area.village && area.mandal && area.district ? { to: { district: area.district, mandal: area.mandal }, label: t("dashboard.back_mandal", { mandal: areaName(area.mandal) }) }
    : area.mandal && area.district ? { to: { district: area.district }, label: t("dashboard.back_district", { district: areaName(area.district) }) }
    : area.district ? { to: {}, label: t("dashboard.back_overview") } : null;
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
        <nav className="drill" aria-label={t("dashboard.path")} data-testid="dash-path">
          {parent && (
            <button className="btn secondary sm drill-back" onClick={() => go(parent.to)}>
              <ArrowLeft aria-hidden="true" />{parent.label}
            </button>
          )}
          <ol>
            {data.path.map((p, i) => (
              <li key={p.level}>
                {i > 0 && <ChevronRight className="drill-sep" size={14} aria-hidden="true" />}
                {i === data.path.length - 1 ? <b aria-current="page">{areaName(p.name)}</b> : <button className="btn quiet" onClick={() => go(p.params)}>{areaName(p.name)}</button>}
              </li>
            ))}
          </ol>
        </nav>
      )}
      <PageState loading={loading && !data} error={error} status={status} onRetry={reload} />
      {data && f && !error && (
        <>
          <FigureRow f={f} area={data.filters} week={data.week} />
          <p className="by-kind" data-testid="by-category">
            <span className="muted">{t("dashboard.by_category")}</span>
            {data.by_category.map((c) => (
              <span key={c.name} className={c.status === "live" ? "" : "planned"}>
                {lang === "te" ? c.label.te : c.label.en} <b className="mono">{c.status === "live" ? c.watched : t("dashboard.planned")}</b>
              </span>
            ))}
          </p>
          <div className="dash-grid">
            <div className="mapbox dash-map">
              <MapView pins={pins} testId="dashboard-map" world avoid={mapPanels} />
              <div className="legend" aria-label={t("dashboard.legend")} ref={legendRef}>
                {(Object.keys(TONE) as Tone[]).map((k) => (
                  <span key={k}><i className="pin" style={{ background: TONE[k].colour }} />{t(`dashboard.tone.${k}`)}</span>
                ))}
              </div>
              {data.area_source && <p className="map-note" ref={noteRef}>{t("dashboard.area_source")}</p>}
            </div>
            <Trend data={data} />
          </div>
          <Children data={data} onOpen={(row) => (row.kind === "asset" ? nav(`/assets/${row.asset_id}`) : go(row.params))} />
        </>
      )}
    </div>
  );
}

function FigureRow({ f, area, week }: { f: Figures; area: Record<string, string>; week: string | null }) {
  const { t } = useTranslation();
  const ack = f.ack_considered ? Math.round((100 * f.ack_on_time) / f.ack_considered) : null;
  type Tile = { k: string; n: number | string; to?: string; tone?: Tone; small?: string };
  const groups: { key: string; tiles: Tile[] }[] = [
    {
      key: "week",
      tiles: [
        { k: "assets", n: f.assets, to: `/assets${query(area)}`, small: t("dashboard.boundary", { n: f.boundary_confirmed, total: f.assets }) },
        { k: "clear_look", n: f.clear_look, to: `/map${query(area)}`, small: f.no_clear_look ? t("dashboard.no_clear_look", { n: f.no_clear_look }) : undefined },
        { k: "changed", n: f.changed, to: incidentsLink(area, week ? { week } : {}), tone: f.changed ? "changed" : undefined },
        { k: "new_incidents", n: f.new_incidents, to: week ? incidentsLink(area, { week }) : undefined },
      ],
    },
    {
      key: "casework",
      tiles: [
        { k: "open", n: f.open, to: incidentsLink(area, { state: "OPEN" }), tone: f.open ? "open" : undefined },
        { k: "under_review", n: f.under_review, to: incidentsLink(area, { state: "UNDER_REVIEW,FIELD_VISIT,FIELD_REPORTED" }), small: f.field_visit ? t("dashboard.on_field_visit", { n: f.field_visit }) : undefined },
        { k: "awaiting_approval", n: f.awaiting_approval, to: incidentsLink(area, { state: "RECOMMENDED" }) },
        { k: "waiting", n: f.waiting, to: incidentsLink(area, { waiting: "true" }), tone: f.waiting ? "waiting" : undefined },
        { k: "confirmed", n: f.confirmed, to: incidentsLink(area, { state: "CONFIRMED" }) },
      ],
    },
    {
      key: "notices",
      tiles: [{ k: "ack", n: ack === null ? "–" : `${ack}%`, to: "/inbox", small: ack === null ? t("dashboard.ack_none") : t("dashboard.ack_of", { n: f.ack_on_time, total: f.ack_considered }) }],
    },
  ];
  return (
    <div className="dash-figures" data-testid="dash-figures">
      {groups.map((g) => (
        <section key={g.key} className={`fig-group fig-${g.key}`} aria-labelledby={`fig-${g.key}-label`}>
          <h2 className="fig-group-label" id={`fig-${g.key}-label`}>{t(`dashboard.group.${g.key}`)}</h2>
          <div className="fig-row">
            {g.tiles.map((x) => (
              <Link key={x.k} to={x.to ?? "/map"} className={`dash-figure link metric-${x.k}${x.tone ? ` tone-${x.tone}` : ""}`} data-testid={`fig-${x.k}`}>
                <b>{x.tone && <i className="tone-dot" style={{ background: TONE[x.tone].colour }} aria-hidden="true" />}{x.n}</b>
                <span>{t(`dashboard.figure.${x.k}`)}</span>
                {x.small && <small>{x.small}</small>}
              </Link>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

/** Two single-series bar charts of the last weeks: one measure each, the latest week marked. */
function Trend({ data }: { data: Overview }) {
  const { t } = useTranslation();
  const [table, setTable] = useState(false);
  return (
    <section className="panel trend" data-testid="trend" aria-labelledby="trend-title">
      <div className="trend-head">
        <h2 className="title-s" id="trend-title">{t("dashboard.trend_title")}</h2>
        {data.trend.length > 0 && (
          <button type="button" className="btn quiet small" aria-expanded={table} onClick={() => setTable((v) => !v)}>
            {table ? t("dashboard.as_chart") : t("dashboard.as_table")}
          </button>
        )}
      </div>
      {data.trend.length === 0 ? (
        <p className="muted small">{t("dashboard.no_week")}</p>
      ) : table ? (
        <table className="grid trend-table">
          <thead>
            <tr><th>{t("dashboard.col.week")}</th><th className="num">{t("dashboard.trend.changed")}</th><th className="num">{t("dashboard.trend.new_incidents")}</th><th className="num">{t("dashboard.figure.clear_look")}</th></tr>
          </thead>
          <tbody>
            {data.trend.map((w) => <tr key={w.week}><td className="mono">{w.week}</td><td className="num">{w.changed}</td><td className="num">{w.new_incidents}</td><td className="num">{w.clear_look}</td></tr>)}
          </tbody>
        </table>
      ) : (
        <>
          <Bars title={t("dashboard.trend.changed")} rows={data.trend.map((w) => ({ week: w.week, n: w.changed }))} />
          <Bars title={t("dashboard.trend.new_incidents")} rows={data.trend.map((w) => ({ week: w.week, n: w.new_incidents }))} />
        </>
      )}
    </section>
  );
}

function Bars({ title, rows }: { title: string; rows: { week: string; n: number }[] }) {
  const [hover, setHover] = useState<number | null>(null);
  const W = 320, H = 108, top = 14, bottom = 20;
  const max = Math.max(1, ...rows.map((r) => r.n));
  const slot = W / rows.length;
  const bw = Math.min(20, slot - 6);
  const shown = hover ?? rows.length - 1;
  return (
    <figure className="bars">
      <figcaption>
        <span>{title}</span>
        <span className="bars-value" aria-live="polite"><span className="mono">{rows[shown].week}</span> <b>{rows[shown].n}</b></span>
      </figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={`${title}: ${rows.map((r) => `${r.week} ${r.n}`).join(", ")}`} onMouseLeave={() => setHover(null)}>
        <line className="bars-grid" x1="0" x2={W} y1={top} y2={top} />
        <line className="bars-axis" x1="0" x2={W} y1={H - bottom} y2={H - bottom} />
        <text className="bars-label" x="0" y={top - 4}>{max}</text>
        {rows.map((r, i) => {
          const h = ((H - top - bottom) * r.n) / max;
          const x = i * slot + (slot - bw) / 2;
          const y = H - bottom - h;
          const rr = Math.min(3, h / 2, bw / 2);
          const d = h > 0 ? `M${x},${H - bottom} V${y + rr} Q${x},${y} ${x + rr},${y} H${x + bw - rr} Q${x + bw},${y} ${x + bw},${y + rr} V${H - bottom} Z` : "";
          const latest = i === rows.length - 1;
          return (
            <g key={r.week} onMouseEnter={() => setHover(i)} onFocus={() => setHover(i)} onBlur={() => setHover(null)} tabIndex={0} aria-label={`${r.week}: ${r.n}`}>
              <rect x={i * slot} y={0} width={slot} height={H} fill="transparent" />
              {d && <path d={d} className={latest ? "bar latest" : "bar"} opacity={hover === null || hover === i ? 1 : 0.5} />}
              {!d && <line className="bars-zero" x1={x} x2={x + bw} y1={H - bottom - 1} y2={H - bottom - 1} />}
              <text className="bars-label" x={i * slot + slot / 2} y={H - 5} textAnchor="middle">{r.week.slice(-3)}</text>
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
    { k: "under_review", rule: { state: "UNDER_REVIEW,FIELD_VISIT,FIELD_REPORTED" } },
    { k: "awaiting_approval", rule: { state: "RECOMMENDED" } },
    { k: "waiting", rule: { waiting: "true" } },
    { k: "confirmed", rule: { state: "CONFIRMED" } },
  ];
  if (data.children.length === 0) return <p className="muted section">{t("dashboard.empty")}</p>;
  return (
    <section className="section">
      <div className="section-head">
        <h2 className="title-s">{t(`dashboard.by.${data.child_level}`)}</h2>
        <span className="small muted">{t("dashboard.table_hint")}</span>
      </div>
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
                    <button className="row-open" onClick={() => onOpen(row)}>{name}<ChevronRight size={14} aria-hidden="true" /></button>
                    {row.kind === "asset" && row.week_status && <div className="small muted">{t(`weeks.status.${row.week_status}`)}</div>}
                    {row.kind === "asset" && row.monitored === false && <div className="small flag">{t("dashboard.not_watched")}</div>}
                  </td>
                  <td><span className="tone"><i style={{ background: TONE[row.tone].colour }} aria-hidden="true" />{t(`dashboard.tone.${row.tone}`)}</span></td>
                  {cols.map((c) => {
                    const n = row.figures[c.k];
                    const to = c.rule && n > 0 ? incidentsLink(row.kind === "asset" ? { asset_id: String(row.asset_id) } : row.params, c.rule) : null;
                    return <td key={c.k} className={`num${n === 0 ? " zero" : ""}`}>{to ? <Link to={to} data-testid={`dash-${row.name}-${c.k}`}>{n}</Link> : n}</td>;
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
