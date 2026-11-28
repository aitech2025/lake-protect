import { useMemo } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api, fmtDate, fmtDateTime } from "../api";
import { BoundarySeal, StatePill, useAsync, usePageTitle } from "../components/Bits";
import { MapView } from "../components/MapView";
import { PageState, TableRegion } from "../components/PageState";
import { Documents, Inspections, WeeklyRecord } from "./AssetRecord";
import { Segmented } from "../components/Segmented";

type Tab = "overview" | "imagery" | "incidents" | "inspections" | "documents" | "audit";
const TABS: Tab[] = ["overview", "imagery", "incidents", "inspections", "documents", "audit"];

export function Asset360() {
  const { id = "" } = useParams();
  const assetId = Number(id);
  const { t, i18n } = useTranslation();
  const [params, setParams] = useSearchParams();
  const tab = (TABS.includes(params.get("tab") as Tab) ? params.get("tab") : "overview") as Tab;
  const { data: feature, error, status, loading, reload } = useAsync(() => api<any>(`/assets/${assetId}`), [assetId]);
  const { data: boundaries } = useAsync(() => api<any>(`/assets/${assetId}/boundaries`), [assetId]);
  const { data: incidents } = useAsync(() => api<any>(`/alerts?asset_id=${assetId}`), [assetId]);
  const { data: audit } = useAsync(() => api<any>(`/audit?entity=asset&entity_id=${assetId}&limit=100`), [assetId]);
  const props = feature?.properties;
  usePageTitle(props ? `${props.name} · ${t("asset360.title")}` : t("asset360.title"));
  const inForce = useMemo(() => boundaries?.features?.filter((f: any) => f.properties.in_force) ?? [], [boundaries]);
  const outline = useMemo(() => ({ type: "FeatureCollection" as const, features: inForce.length ? inForce : feature?.geometry ? [{ type: "Feature", id: assetId, properties: { kind: props?.boundary_kind, status: props?.boundary_status }, geometry: feature.geometry }] : [] }), [inForce, feature, assetId, props]);
  const name = i18n.language === "te" && props?.name_te ? props.name_te : props?.name;

  if (!feature) return <div className="page"><PageState loading={loading} error={error} status={status} onRetry={reload} /></div>;
  return <div className="page asset360" data-testid="asset360">
    <header className="asset360-head">
      <div>
        <p className="crumbs"><Link to="/assets">{t("asset360.back")}</Link><span aria-hidden="true">/</span><span>{t("asset360.kicker")}</span></p>
        <h1>{name}</h1>
        <p className="muted"><span className="mono">{props.asset_code ?? props.platform_asset_id ?? props.asset_key}</span>, {[props.district, props.mandal, props.village].filter(Boolean).join(", ") || t("dashboard.not_recorded")}</p>
      </div>
      <div className="asset360-badges"><span className={`pill ${props.monitored ? "ok" : "closed"}`}>{props.monitored ? t("asset360.watched") : t("locations.not_watched")}</span><BoundarySeal status={props.boundary_status} version={props.boundary_version} /></div>
    </header>
    <div className="asset360-tabs">
      <Segmented mode="tabs" label={t("asset360.sections")} value={tab} onChange={(key) => setParams({ tab: key })} options={TABS.map((key) => ({ value: key, label: t(`asset360.tab.${key}`) }))} />
    </div>

    {tab === "overview" && <>
      <section className="asset360-summary">
        <div><span>{t("asset360.asset_code")}</span><b className="mono">{props.asset_code ?? props.platform_asset_id ?? props.asset_key}</b></div>
        <div><span>{t("asset360.baseline")}</span><b>{fmtDate(props.baseline_date, i18n.language)}</b></div>
        <div><span>{t("asset360.category")}</span><b>{t(`registry.category_name.${props.category}`, { defaultValue: props.category })}</b></div>
        <div><span>{t("assets.col.extent")}</span><b>{props.area_acres != null ? t("assets.acres", { acres: props.area_acres }) : "—"}</b></div>
        <div><span>{t("asset360.latest_look")}</span><b>{props.screened_as_of ? fmtDate(props.screened_as_of, i18n.language) : t("weeks.none")}</b><small>{props.screen_status ? t(`weeks.status.${props.screen_status}`) : ""}</small></div>
        <div><span>{t("asset360.open_incidents")}</span><b>{incidents?.count ?? incidents?.items?.length ?? "—"}</b></div>
      </section>
      <div className="asset360-overview-grid">
        <section className="panel"><h2 className="title-s">{t("asset360.boundary")}</h2><div className="mapbox" style={{ height: 390 }}><MapView boundaries={outline} testId="asset360-map" /></div><p className="small muted">{t("assets.boundary_source")}: {props.boundary_source ?? t("dashboard.not_recorded")}</p></section>
        <section className="panel"><h2 className="title-s">{t("asset360.identity")}</h2><dl className="facts"><dt>{t("asset360.district")}</dt><dd>{props.district ?? t("dashboard.not_recorded")}</dd><dt>{t("asset360.mandal")}</dt><dd>{props.mandal ?? t("dashboard.not_recorded")}</dd><dt>{t("asset360.village")}</dt><dd>{props.village ?? t("dashboard.not_recorded")}</dd><dt>{t("asset360.baseline")}</dt><dd>{fmtDate(props.baseline_date, i18n.language)}</dd><dt>{t("asset360.provenance")}</dt><dd>{props.boundary_source ?? t("dashboard.not_recorded")}</dd><dt>{t("asset360.boundary_status")}</dt><dd><BoundarySeal status={props.boundary_status} version={props.boundary_version} /></dd></dl><Link className="btn secondary" to={`/assets?asset=${assetId}`}>{t("asset360.manage")}</Link></section>
      </div>
      <section className="section"><h2 className="title-s">{t("asset360.recent_incidents")}</h2>{!incidents?.items?.length ? <p className="muted">{t("queue.empty_real")}</p> : <ul className="asset360-incident-list">{incidents.items.slice(0, 5).map((a: any) => <li key={a.id}><Link to={`/alerts/${a.id}`}>{a.code} · {a.change_label}</Link><StatePill state={a.state} /><span className="small muted">{fmtDateTime(a.created_at, i18n.language)}</span></li>)}</ul>}</section>
    </>}
    {tab === "imagery" && <WeeklyRecord assetId={assetId} />}
    {tab === "documents" && <><Documents assetId={assetId} /><section className="panel"><h2 className="title-s">{t("asset360.boundary_versions")}</h2>{!boundaries?.features?.length ? <p className="muted">{t("assets.versions")}</p> : <TableRegion label={t("asset360.boundary_versions")}><table className="grid"><thead><tr><th>{t("assets.source")}</th><th>{t("detail.boundary")}</th><th>{t("asset360.version")}</th><th>{t("asset360.valid_from")}</th></tr></thead><tbody>{boundaries.features.map((f: any) => <tr key={f.id}><td>{f.properties.source_name}</td><td><BoundarySeal status={f.properties.status} /></td><td>{f.properties.version}</td><td>{fmtDate(f.properties.valid_from, i18n.language)}</td></tr>)}</tbody></table></TableRegion>}</section></>}
    {tab === "incidents" && <section className="panel"><h2 className="title-s">{t("asset360.incident_history")}</h2>{!incidents?.items?.length ? <p className="muted">{t("queue.empty_real")}</p> : <TableRegion label={t("asset360.incident_history")}><table className="grid"><thead><tr><th>{t("asset360.incident")}</th><th>{t("queue.what_changed")}</th><th>{t("queue.state")}</th><th>{t("audit.when")}</th></tr></thead><tbody>{incidents.items.map((a: any) => <tr key={a.id}><td><Link to={`/alerts/${a.id}`}>{a.code}</Link></td><td>{a.change_label}</td><td><StatePill state={a.state} /></td><td>{fmtDateTime(a.created_at, i18n.language)}</td></tr>)}</tbody></table></TableRegion>}</section>}
    {tab === "inspections" && <Inspections assetId={assetId} />}
    {tab === "audit" && <section className="panel"><h2 className="title-s">{t("asset360.audit_history")}</h2>{!audit?.items?.length ? <p className="muted">{t("asset360.audit_empty")}</p> : <TableRegion label={t("asset360.audit_history")}><table className="grid"><thead><tr><th>{t("audit.when")}</th><th>{t("audit.who")}</th><th>{t("audit.what")}</th><th>{t("audit.item")}</th></tr></thead><tbody>{audit.items.map((a: any) => <tr key={a.id}><td>{fmtDateTime(a.at, i18n.language)}</td><td>{a.actor}</td><td>{a.action}</td><td><code>{JSON.stringify(a.details)}</code></td></tr>)}</tbody></table></TableRegion>}</section>}
  </div>;
}
