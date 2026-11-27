import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../api";
import { MapView, type Pin } from "../components/MapView";
import { useAsync, usePageTitle } from "../components/Bits";

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

export function MapPage() {
  const { t, i18n } = useTranslation();
  const nav = useNavigate();
  const { data } = useAsync(() => api<{ features: any[] }>("/assets"), []);
  usePageTitle(t("nav.map"));
  const pins: Pin[] = useMemo(() => (data?.features ?? []).flatMap((f) => {
    const p = point(f.geometry);
    if (!p) return [];
    return [{ id: f.id, lon: p[0], lat: p[1], colour: f.properties.category === "water_body" ? "#187ca3" : "#bd8b32",
      label: i18n.language === "te" && f.properties.name_te ? f.properties.name_te : f.properties.name,
      onClick: () => nav(`/assets/${f.id}`) }];
  }), [data, i18n.language, nav]);
  return <main className="full-map-page" data-testid="full-map-page"><header className="full-map-head"><div><p className="eyebrow">GEOGUARD / TELANGANA</p><h1>{t("nav.map")}</h1><p className="muted">{t("map.assets_count", { count: pins.length })}</p></div><button className="btn secondary" onClick={() => nav("/dashboard")}>{t("dashboard.title")}</button></header><div className="full-map-frame"><MapView pins={pins} testId="full-asset-map" /></div></main>;
}
