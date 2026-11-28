/* eslint-disable @typescript-eslint/no-explicit-any */
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../api";
import { MapView, type Pin } from "../components/MapView";
import { useAsync, usePageTitle } from "../components/Bits";
import { Segmented } from "../components/Segmented";

const LAKE = "#2f8fc4";
const LAND = "#c79a3e";
const STOPPED = "#8b97a3";

function point(geometry: any): [number, number] | null {
  const coords: number[][] = [];
  const walk = (v: any) => {
    if (Array.isArray(v) && typeof v[0] === "number" && typeof v[1] === "number") coords.push(v as number[]);
    else if (Array.isArray(v)) v.forEach(walk);
  };
  walk(geometry?.coordinates);
  if (!coords.length) return null;
  return [coords.reduce((n, p) => n + p[0], 0) / coords.length, coords.reduce((n, p) => n + p[1], 0) / coords.length];
}

/** Every watched location on the satellite base map; a pin opens its record. */
export function MapPage() {
  const { t, i18n } = useTranslation();
  const nav = useNavigate();
  const { data } = useAsync(() => api<{ features: any[] }>("/assets"), []);
  const [kind, setKind] = useState<"all" | "lakes" | "lands">("all");
  usePageTitle(t("nav.map"));
  const features = useMemo(() => (data?.features ?? []).filter((f) => kind === "all" || (kind === "lakes" ? f.properties.category === "water_body" : f.properties.category !== "water_body")), [data, kind]);
  const pins: Pin[] = useMemo(() => features.flatMap((f) => {
    const p = point(f.geometry);
    if (!p) return [];
    return [{ id: f.id, lon: p[0], lat: p[1], colour: f.properties.monitored === false ? STOPPED : f.properties.category === "water_body" ? LAKE : LAND,
      label: i18n.language === "te" && f.properties.name_te ? f.properties.name_te : f.properties.name,
      onClick: () => nav(`/assets/${f.id}`) }];
  }), [features, i18n.language, nav]);
  const counts = useMemo(() => {
    const all = data?.features ?? [];
    const lakes = all.filter((f) => f.properties.category === "water_body").length;
    return { all: all.length, lakes, lands: all.length - lakes };
  }, [data]);
  return (
    <section className="full-map-page" aria-labelledby="full-map-title" data-testid="full-map-page">
      <div className="full-map-frame"><MapView pins={pins} testId="full-asset-map" /></div>
      <header className="full-map-head">
        <div>
          <h1 id="full-map-title">{t("nav.map")}</h1>
          <p className="muted small">{data ? t("map.assets_count", { count: pins.length }) : t("error.loading")}</p>
        </div>
        <Segmented
          label={t("map.show")}
          value={kind}
          onChange={setKind}
          options={(["all", "lakes", "lands"] as const).map((k) => ({ value: k, label: t(k === "all" ? "group.all" : `assets.tab.${k}`), count: data ? counts[k] : null }))}
        />
        <p className="small muted">{t("map.hint")}</p>
      </header>
      <div className="legend map-legend" aria-label={t("dashboard.legend")}>
        <span><i className="legend-dot" style={{ background: LAKE }} />{t("map.legend_lake")}</span>
        <span><i className="legend-dot" style={{ background: LAND }} />{t("map.legend_land")}</span>
        <span><i className="legend-dot" style={{ background: STOPPED }} />{t("map.legend_stopped")}</span>
      </div>
    </section>
  );
}
