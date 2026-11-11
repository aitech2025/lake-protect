/* eslint-disable @typescript-eslint/no-explicit-any */
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, fmtDate } from "../api";
import { BoundarySeal, useAsync, usePageTitle } from "../components/Bits";
import { MapView } from "../components/MapView";
import { PageState, TableRegion } from "../components/PageState";
import { DemoTag, useDemoOnScreen } from "../demo";

export function Assets() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const [dataset, setDataset] = useState<"demo" | "real">("demo");
  const [selected, setSelected] = useState<number | null>(null);
  const { data, error, status, loading, reload } = useAsync(() => api<{ features: any[] }>("/assets"), []);
  const features = useMemo(() => (data?.features ?? []).filter((f) => f.properties.is_demo === (dataset === "demo")), [data, dataset]);
  useDemoOnScreen(dataset === "demo" && features.length > 0);
  usePageTitle(t("assets.title"));
  const { data: versions } = useAsync(() => (selected ? api<{ features: any[] }>(`/assets/${selected}/boundaries`) : Promise.resolve(null)), [selected]);

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
        <div className="chips">
          <button className="chip" aria-pressed={dataset === "demo"} onClick={() => { setDataset("demo"); setSelected(null); }}>{t("assets.dataset_demo")}</button>
          <button className="chip" aria-pressed={dataset === "real"} onClick={() => { setDataset("real"); setSelected(null); }} data-testid="dataset-real">{t("assets.dataset_real")}</button>
        </div>
      </div>
      {dataset === "real" && <p className="note" style={{ marginBottom: "1rem" }}>{t("assets.real_note")}</p>}
      <PageState loading={loading && !data} error={error} status={status} onRetry={reload} />
      <div className="queue" style={{ height: "auto" }}>
        <div className="mapbox" style={{ height: 520 }}>
          <MapView boundaries={selected ? selectedFc : mapFc} />
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
    </div>
  );
}
