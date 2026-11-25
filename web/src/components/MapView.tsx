import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";
import { API_BASE } from "../api";

export type Pin = { id: number | string; lon: number; lat: number; colour: string; label?: string; big?: boolean; onClick?: () => void };

type Props = {
  boundaries?: GeoJSON.FeatureCollection; // features with properties.kind and properties.status
  changes?: GeoJSON.FeatureCollection;
  pins?: Pin[];
  fit?: [number, number, number, number] | null;
  height?: string;
  testId?: string;
  theme?: "dark" | "light";
  layerVisibility?: { boundaries?: boolean; ftl?: boolean; changes?: boolean };
  onAssetClick?: (id: number) => void;
  interactive?: boolean;
  measure?: boolean;
  onMeasureChange?: (metres: number) => void;
};

const EMPTY: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };
const CONFIRMED = ["physically_marked", "final_notification", "surveyed_agency"];

// Offline style: local demo tiles, no glyphs or sprites, so no request leaves the machine.
const STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    base: { type: "raster", tiles: [`${API_BASE}/tiles/demo/{z}/{x}/{y}.png`], tileSize: 256, maxzoom: 17, attribution: "Demo map (fictional)" },
  },
  layers: [
    { id: "bg", type: "background", paint: { "background-color": "#f0ece2" } },
    { id: "base", type: "raster", source: "base" },
  ],
};

function withCertainty(fc: GeoJSON.FeatureCollection): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: fc.features.map((f) => {
      const status = String(f.properties?.status ?? "");
      const certainty = CONFIRMED.includes(status) ? "confirmed" : status === "preliminary_notification" ? "preliminary" : "estimated";
      return { ...f, properties: { ...f.properties, certainty } };
    }),
  };
}

function bboxOf(fcs: GeoJSON.FeatureCollection[]): [number, number, number, number] | null {
  let w = Infinity, s = Infinity, e = -Infinity, n = -Infinity;
  const walk = (c: unknown): void => {
    if (Array.isArray(c) && typeof c[0] === "number") {
      const [x, y] = c as number[];
      w = Math.min(w, x); e = Math.max(e, x); s = Math.min(s, y); n = Math.max(n, y);
    } else if (Array.isArray(c)) c.forEach(walk);
  };
  fcs.forEach((fc) => fc.features.forEach((f) => walk(f.geometry?.coordinates)));
  return Number.isFinite(w) ? [w, s, e, n] : null;
}

export function MapView({ boundaries = EMPTY, changes = EMPTY, pins = [], fit, height = "100%", testId, theme: themeProp, layerVisibility = {}, onAssetClick, interactive = true, measure = false, onMeasureChange }: Props) {
  const [globalTheme, setGlobalTheme] = useState<"dark" | "light">(() => document.documentElement.dataset.theme === "light" ? "light" : "dark");
  const theme = themeProp ?? globalTheme;
  useEffect(() => {
    const sync = (event: Event) => setGlobalTheme((event as CustomEvent<"dark" | "light">).detail);
    window.addEventListener("geoguard:theme", sync);
    return () => window.removeEventListener("geoguard:theme", sync);
  }, []);
  const ref = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const markers = useRef<maplibregl.Marker[]>([]);
  const loaded = useRef(false);
  const onAssetClickRef = useRef(onAssetClick);
  const onMeasureChangeRef = useRef(onMeasureChange);
  useEffect(() => { onAssetClickRef.current = onAssetClick; }, [onAssetClick]);
  useEffect(() => { onMeasureChangeRef.current = onMeasureChange; }, [onMeasureChange]);

  useEffect(() => {
    if (!ref.current) return;
    const m = new maplibregl.Map({ container: ref.current, style: STYLE, center: [81.5, 14.5], zoom: 13, interactive, attributionControl: { compact: true }, maxZoom: 18 });
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    m.on("load", () => {
      m.addSource("boundaries", { type: "geojson", data: EMPTY });
      m.addSource("changes", { type: "geojson", data: EMPTY });
      m.addSource("measure", { type: "geojson", data: EMPTY });
      const isKind = (k: string[]) => ["in", ["get", "kind"], ["literal", k]] as maplibregl.ExpressionSpecification;
      m.addLayer({ id: "ring", type: "line", source: "boundaries", filter: isKind(["watch_ring"]), paint: { "line-color": "#75848b", "line-width": 1.2, "line-dasharray": [1, 3] } });
      m.addLayer({ id: "buffer", type: "line", source: "boundaries", filter: isKind(["buffer"]), paint: { "line-color": "#c4402f", "line-width": 1.6, "line-dasharray": [3, 2] } });
      const primary = ["ftl", "parcel"];
      const certaintyIs = (c: string) => ["all", isKind(primary), ["==", ["get", "certainty"], c]] as maplibregl.FilterSpecification;
      m.addLayer({ id: "primary-fill", type: "fill", source: "boundaries", filter: isKind(primary), paint: { "fill-color": "#1f6fa8", "fill-opacity": 0.06 } });
      m.addLayer({ id: "primary-confirmed", type: "line", source: "boundaries", filter: certaintyIs("confirmed"), paint: { "line-color": "#1f6fa8", "line-width": 2.6 } });
      m.addLayer({ id: "primary-preliminary", type: "line", source: "boundaries", filter: certaintyIs("preliminary"), paint: { "line-color": "#1f6fa8", "line-width": 2.6, "line-dasharray": [3, 2] } });
      m.addLayer({ id: "primary-estimated", type: "line", source: "boundaries", filter: certaintyIs("estimated"), paint: { "line-color": "#1f6fa8", "line-width": 2.6, "line-dasharray": [0.6, 2] } });
      const assetClick = (event: maplibregl.MapLayerMouseEvent) => {
        const feature = event.features?.[0];
        const raw = feature?.properties?.id ?? feature?.id;
        const id = Number(raw);
        if (Number.isFinite(id)) onAssetClickRef.current?.(id);
      };
      m.on("click", "primary-fill", assetClick);
      m.on("mouseenter", "primary-fill", () => { m.getCanvas().style.cursor = "pointer"; });
      m.on("mouseleave", "primary-fill", () => { m.getCanvas().style.cursor = ""; });
      m.addLayer({ id: "change-fill", type: "fill", source: "changes", paint: { "fill-color": "#e0a526", "fill-opacity": 0.55 } });
      m.addLayer({ id: "change-line", type: "line", source: "changes", paint: { "line-color": "#7a4f05", "line-width": 1.6 } });
      m.addLayer({ id: "measure-line", type: "line", source: "measure", filter: ["==", ["geometry-type"], "LineString"], paint: { "line-color": "#06b6d4", "line-width": 2.5, "line-dasharray": [2, 1] } });
      m.addLayer({ id: "measure-points", type: "circle", source: "measure", filter: ["==", ["geometry-type"], "Point"], paint: { "circle-radius": 4, "circle-color": "#06b6d4", "circle-stroke-color": "#ffffff", "circle-stroke-width": 1.5 } });
      loaded.current = true;
      m.fire("lp:data");
    });
    map.current = m;
    return () => {
      m.remove();
      map.current = null;
      loaded.current = false;
    };
  }, []);

  useEffect(() => {
    const m = map.current;
    if (!m) return;
    const apply = () => {
      (m.getSource("boundaries") as maplibregl.GeoJSONSource | undefined)?.setData(withCertainty(boundaries) as never);
      (m.getSource("changes") as maplibregl.GeoJSONSource | undefined)?.setData(changes as never);
      const shapes = fit ?? bboxOf([boundaries, changes]);
      const pinBox = pins.length ? bboxOf([{ type: "FeatureCollection", features: pins.map((p) => ({ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [p.lon, p.lat] } })) }]) : null;
      // Pins alone stay at district scale; shapes may zoom in to street level.
      if (shapes) m.fitBounds(shapes, { padding: 48, duration: 0, maxZoom: 16.5 });
      else if (pinBox) m.fitBounds(pinBox, { padding: 60, duration: 0, maxZoom: 14 });
    };
    if (loaded.current) apply();
    else m.once("lp:data", apply);
  }, [boundaries, changes, fit, pins]);


  useEffect(() => {
    const m = map.current;
    if (!m) return;
    const apply = () => {
      const visible = (name: string, on: boolean) => {
        if (m.getLayer(name)) m.setLayoutProperty(name, "visibility", on ? "visible" : "none");
      };
      visible("primary-fill", layerVisibility.boundaries ?? true);
      visible("primary-confirmed", layerVisibility.boundaries ?? true);
      visible("primary-preliminary", layerVisibility.boundaries ?? true);
      visible("primary-estimated", layerVisibility.boundaries ?? true);
      visible("ring", layerVisibility.boundaries ?? true);
      visible("buffer", layerVisibility.ftl ?? true);
      visible("change-fill", layerVisibility.changes ?? true);
      visible("change-line", layerVisibility.changes ?? true);
      m.setPaintProperty("bg", "background-color", theme === "dark" ? "#090e17" : "#f8fafc");
      if (m.getLayer("base")) {
        m.setPaintProperty("base", "raster-brightness-min", theme === "dark" ? 0.03 : 0);
        m.setPaintProperty("base", "raster-brightness-max", theme === "dark" ? 0.42 : 1);
        m.setPaintProperty("base", "raster-saturation", theme === "dark" ? -0.55 : 0);
      }
    };
    if (loaded.current) apply();
    else m.once("lp:data", apply);
  }, [theme, layerVisibility.boundaries, layerVisibility.ftl, layerVisibility.changes]);


  useEffect(() => {
    const m = map.current;
    if (!m) return;
    let points: [number, number][] = [];
    const distance = (a: [number, number], b: [number, number]) => {
      const rad = Math.PI / 180;
      const dLat = (b[1] - a[1]) * rad;
      const dLon = (b[0] - a[0]) * rad;
      const x = Math.sin(dLat / 2) ** 2 + Math.cos(a[1] * rad) * Math.cos(b[1] * rad) * Math.sin(dLon / 2) ** 2;
      return 6371008.8 * 2 * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
    };
    const render = () => {
      const features: GeoJSON.Feature[] = points.map((p) => ({ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: p } }));
      if (points.length > 1) features.push({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: points } });
      (m.getSource("measure") as maplibregl.GeoJSONSource | undefined)?.setData({ type: "FeatureCollection", features });
      let total = 0;
      for (let i = 1; i < points.length; i++) total += distance(points[i - 1], points[i]);
      onMeasureChangeRef.current?.(total);
    };
    const click = (event: maplibregl.MapMouseEvent) => {
      points.push([event.lngLat.lng, event.lngLat.lat]);
      render();
    };
    const attach = () => {
      if (measure && interactive) {
        points = [];
        render();
        m.getCanvas().style.cursor = "crosshair";
        m.on("click", click);
      } else {
        points = [];
        render();
        m.off("click", click);
        m.getCanvas().style.cursor = "";
      }
    };
    if (loaded.current) attach();
    else m.once("lp:data", attach);
    return () => {
      m.off("click", click);
      m.getCanvas().style.cursor = "";
    };
  }, [measure, interactive]);

  useEffect(() => {
    const m = map.current;
    if (!m) return;
    const zoom = (event: Event) => {
      const amount = Number((event as CustomEvent<number>).detail ?? 0);
      m.zoomTo(m.getZoom() + amount, { duration: 220 });
    };
    const tilt = (event: Event) => {
      const enabled = Boolean((event as CustomEvent<boolean>).detail);
      m.easeTo({ pitch: enabled ? 48 : 0, duration: 350 });
    };
    window.addEventListener("geoguard:zoom", zoom);
    window.addEventListener("geoguard:tilt", tilt);
    return () => { window.removeEventListener("geoguard:zoom", zoom); window.removeEventListener("geoguard:tilt", tilt); };
  }, []);

  useEffect(() => {
    const m = map.current;
    if (!m) return;
    markers.current.forEach((mk) => mk.remove());
    markers.current = pins.map((p) => {
      const el = document.createElement("div");
      el.className = "pin-wrap";
      const dot = document.createElement("button");
      dot.className = `pin${p.big ? " big" : ""}`;
      dot.style.background = p.colour;
      dot.setAttribute("aria-label", p.label ?? String(p.id));
      dot.dataset.alertId = String(p.id);
      if (p.onClick) dot.addEventListener("click", p.onClick);
      el.appendChild(dot);
      if (p.label && p.big) {
        const label = document.createElement("div");
        label.className = "pin-label";
        label.textContent = p.label;
        el.appendChild(label);
      }
      return new maplibregl.Marker({ element: el, anchor: "center" }).setLngLat([p.lon, p.lat]).addTo(m);
    });
  }, [pins]);

  return <div ref={ref} style={{ height, width: "100%" }} data-testid={testId} />;
}
