/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api, fmtDate } from "../api";
import { BoundarySeal, useAsync, usePageTitle } from "../components/Bits";
import { MapView } from "../components/MapView";
import { PageState, TableRegion } from "../components/PageState";
import { baseFor, useDataset } from "../dataset";
import { DemoTag, useDemoOnScreen } from "../demo";
import { Documents, WeeklyRecord } from "./AssetRecord";
import { CoverageLine, ScreeningSummary } from "./Screening";

export function Assets() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const { dataset } = useDataset();
  const [params] = useSearchParams();
  const linked = params.get("asset");
  const [selected, setSelected] = useState<number | null>(linked ? Number(linked) : null);
  const [firstDataset] = useState(dataset);
  useEffect(() => {
    if (dataset !== firstDataset) setSelected(null);
  }, [dataset, firstDataset]);
  const { data, error, status, loading, reload } = useAsync(() => api<{ features: any[] }>(`/assets?dataset=${dataset}`), [dataset]);
  const features = useMemo(() => (data?.features ?? []).filter((f) => f.properties.is_demo === (dataset === "demo")), [data, dataset]);
  useDemoOnScreen(dataset === "demo" && features.length > 0);
  usePageTitle(t("assets.title"));
  const { data: versions } = useAsync(() => (selected ? api<{ features: any[] }>(`/assets/${selected}/boundaries`) : Promise.resolve(null)), [selected]);
  const { data: register } = useAsync(() => (selected ? api<any>(`/assets/${selected}/register`) : Promise.resolve(null)), [selected]);

  const mapFc = useMemo(
    () => ({
      type: "FeatureCollection" as const,
      features: features.filter((f) => f.geometry).map((f) => ({ ...f, properties: { kind: f.properties.boundary_kind, status: f.properties.boundary_status } })),
    }),
    [features],
  );
  const selectedFc = useMemo(
    () => (versions ? { type: "FeatureCollection" as const, features: versions.features.filter((f) => f.properties.in_force) } : mapFc),
    [versions, mapFc],
  );

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>{t("assets.title")}</h1>
          <p className="muted" aria-hidden={!data}>{data ? features.length : " "}</p>
        </div>
      </div>
      {dataset === "real" && <p className="note" style={{ marginBottom: "1rem" }}>{t("assets.real_note")}</p>}
      {dataset === "real" && <ScreeningSummary />}
      <PageState loading={loading && !data} error={error} status={status} onRetry={reload} />
      <div className="queue" style={{ height: "auto" }}>
        <div className="mapbox" style={{ height: 520 }}>
          <MapView base={baseFor(dataset)} boundaries={selected ? selectedFc : mapFc} />
        </div>
        <div className="list" style={{ maxHeight: 520 }}>
          {features.map((f) => {
            const p = f.properties;
            return (
              <button key={f.id} className="row" style={{ width: "100%", border: 0, background: selected === f.id ? "#eef3f0" : "transparent", textAlign: "left" }} onClick={() => setSelected(f.id)}>
                <span className="bar" style={{ background: "#1f6fa8" }} />
                <span>
                  <h3>{lang === "te" && p.name_te ? p.name_te : p.name} {p.is_demo && <DemoTag />}</h3>
                  <span className="meta">
                    <span>{t(`cohort.${p.cohort}`)}</span>
                    <span>{t(`mode.${p.mode}`)}</span>
                    {p.area_acres !== null && <span>{t("assets.acres", { acres: p.area_acres })}</span>}
                    <span>{t("assets.baseline", { date: fmtDate(p.baseline_date, lang) })}</span>
                  </span>
                  {!p.is_demo && <CoverageLine p={p} />}
                </span>
                <span><BoundarySeal status={p.boundary_status} version={p.boundary_version} /></span>
              </button>
            );
          })}
        </div>
      </div>
      {versions && (
        <section className="section">
          <h2>{t("assets.versions")}</h2>
          <TableRegion label={t("assets.versions")}>
            <table className="grid" data-testid="boundary-versions">
              <thead>
                <tr><th>#</th><th>{t("detail.boundary")}</th><th>{t("assets.source")}</th><th /></tr>
              </thead>
              <tbody>
                {versions.features.filter((f) => ["ftl", "parcel"].includes(f.properties.kind)).map((f) => {
                  const p = f.properties;
                  return (
                    <tr key={p.id}>
                      <td>{p.version}</td>
                      <td><BoundarySeal status={p.status} /></td>
                      <td>
                        {p.source_url ? <a href={p.source_url} target="_blank" rel="noreferrer">{p.source_name}</a> : p.source_name}
                        {p.notification_ref && <div className="small muted">{p.notification_ref}</div>}
                        <div className="small muted">{t("assets.valid", { from: fmtDate(p.valid_from, lang) })}{p.effective_valid_to ? ` ${t("assets.until", { to: fmtDate(p.effective_valid_to, lang) })}` : ""}</div>
                      </td>
                      <td>{p.in_force ? t("assets.in_force") : t("assets.superseded")}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </TableRegion>
        </section>
      )}
      {selected && <WeeklyRecord assetId={selected} />}
      {selected && <Documents assetId={selected} />}
      {register && (
        <section className="section" data-testid="asset-register">
          <h2>{t("assets.register")}</h2>
          {register.links.length === 0 ? (
            <p className="muted">{t("assets.no_links")}</p>
          ) : (
            <ul className="contract">
              {register.links.map((l: any) => (
                <li key={`${l.connector}:${l.external_id}`}>
                  <b>{l.agency}</b>: <code>{l.external_id}</code>
                  <div className="small muted">{l.file_name} · {fmtDate(l.source_date, lang)} · SHA-256 {String(l.sha256).slice(0, 12)}…</div>
                </li>
              ))}
            </ul>
          )}
          <h3 style={{ marginTop: "1rem" }}>{t("assets.parcels")}</h3>
          {register.parcels.length === 0 ? (
            <p className="muted">{t("assets.no_parcels")}</p>
          ) : (
            <>
              {register.core_area_sq_m > 0 && <p className="note" style={{ marginBottom: "0.6rem" }}>{t("assets.core_area", { area: Math.round(register.core_area_sq_m).toLocaleString("en-IN") })}</p>}
              <TableRegion label={t("assets.parcels")}>
                <table className="grid" data-testid="asset-parcels">
                  <thead>
                    <tr><th>{t("assets.col.survey")}</th><th>{t("assets.col.village")}</th><th>{t("assets.col.category")}</th><th>{t("assets.col.extent")}</th><th>{t("assets.col.zone")}</th></tr>
                  </thead>
                  <tbody>
                    {register.parcels.map((p: any) => (
                      <tr key={`${p.village}:${p.survey_no}:${p.sub_division}`}>
                        <td>{p.survey_no}{p.sub_division ? `/${p.sub_division}` : ""}{p.bhudhaar && <div className="small muted">{p.bhudhaar}</div>}</td>
                        <td>{p.village}</td>
                        <td>{t(`land.${p.land_category}`)}{p.core && <b> · {t("assets.core")}</b>}</td>
                        <td>{p.extent_acres ?? ""}</td>
                        <td>{t(`assets.where.${p.zone}`)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableRegion>
            </>
          )}
        </section>
      )}
    </div>
  );
}
