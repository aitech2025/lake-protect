import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";
import { API_BASE } from "../api";

export type Pin = { id: number | string; lon: number; lat: number; colour: string; label?: string; big?: boolean; onClick?: () => void };

type Props = {
  /** "s2": the Sentinel-2 mosaic of real Hyderabad; "demo": the drawn fictional world. */
  base?: "demo" | "s2";
  boundaries?: GeoJSON.FeatureCollection; // features with properties.kind and properties.status
  changes?: GeoJSON.FeatureCollection;
  pins?: Pin[];
  fit?: [number, number, number, number] | null;
  height?: string;
  testId?: string;
};

const EMPTY: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };
const CONFIRMED = ["physically_marked", "final_notification", "surveyed_agency"];

// Offline styles: local tiles, no glyphs or sprites, so no request leaves the machine.
const STYLES: Record<"demo" | "s2", maplibregl.StyleSpecification> = {
  demo: {
    version: 8,
    sources: {
      base: { type: "raster", tiles: [`${API_BASE}/tiles/demo/{z}/{x}/{y}.png`], tileSize: 256, maxzoom: 17, attribution: "Demo map (fictional)" },
    },
    layers: [
      { id: "bg", type: "background", paint: { "background-color": "#f0ece2" } },
      { id: "base", type: "raster", source: "base" },
    ],
  },
  // Real Hyderabad: Sentinel-2 at 10 m, made by `lp basemap`. Zoom 14 is the finest level made,
  // so closer views enlarge it rather than suggest detail the data does not have.
  s2: {
    version: 8,
    sources: {
      base: {
        type: "raster",
        tiles: [`${API_BASE}/tiles/s2/{z}/{x}/{y}.jpg`],
        tileSize: 256,
        minzoom: 9,
        maxzoom: 14,
        attribution: "Contains modified Copernicus Sentinel data · Lake outlines © OpenStreetMap contributors",
      },
    },
    layers: [
      { id: "bg", type: "background", paint: { "background-color": "#262a28" } },
      { id: "base", type: "raster", source: "base" },
    ],
  },
};
const CENTRE: Record<"demo" | "s2", [number, number]> = { demo: [81.5, 14.5], s2: [78.47, 17.41] };

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

export function MapView({ base = "demo", boundaries = EMPTY, changes = EMPTY, pins = [], fit, height = "100%", testId }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const markers = useRef<maplibregl.Marker[]>([]);
  const loaded = useRef(false);
  const [generation, setGeneration] = useState(0);

  useEffect(() => {
    if (!ref.current) return;
    const m = new maplibregl.Map({ container: ref.current, style: STYLES[base], center: CENTRE[base], zoom: base === "s2" ? 10 : 13, attributionControl: { compact: true }, maxZoom: 18 });
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    m.on("load", () => {
      m.addSource("boundaries", { type: "geojson", data: EMPTY });
      m.addSource("changes", { type: "geojson", data: EMPTY });
      const isKind = (k: string[]) => ["in", ["get", "kind"], ["literal", k]] as maplibregl.ExpressionSpecification;
      m.addLayer({ id: "ring", type: "line", source: "boundaries", filter: isKind(["watch_ring"]), paint: { "line-color": "#75848b", "line-width": 1.2, "line-dasharray": [1, 3] } });
      m.addLayer({ id: "buffer", type: "line", source: "boundaries", filter: isKind(["buffer"]), paint: { "line-color": "#c4402f", "line-width": 1.6, "line-dasharray": [3, 2] } });
      const primary = ["ftl", "parcel"];
      const certaintyIs = (c: string) => ["all", isKind(primary), ["==", ["get", "certainty"], c]] as maplibregl.FilterSpecification;
      m.addLayer({ id: "primary-fill", type: "fill", source: "boundaries", filter: isKind(primary), paint: { "fill-color": "#1f6fa8", "fill-opacity": 0.06 } });
      m.addLayer({ id: "primary-confirmed", type: "line", source: "boundaries", filter: certaintyIs("confirmed"), paint: { "line-color": "#1f6fa8", "line-width": 2.6 } });
      m.addLayer({ id: "primary-preliminary", type: "line", source: "boundaries", filter: certaintyIs("preliminary"), paint: { "line-color": "#1f6fa8", "line-width": 2.6, "line-dasharray": [3, 2] } });
      m.addLayer({ id: "primary-estimated", type: "line", source: "boundaries", filter: certaintyIs("estimated"), paint: { "line-color": "#1f6fa8", "line-width": 2.6, "line-dasharray": [0.6, 2] } });
      m.addLayer({ id: "change-fill", type: "fill", source: "changes", paint: { "fill-color": "#e0a526", "fill-opacity": 0.55 } });
      m.addLayer({ id: "change-line", type: "line", source: "changes", paint: { "line-color": "#7a4f05", "line-width": 1.6 } });
      loaded.current = true;
      m.fire("lp:data");
    });
    map.current = m;
    setGeneration((g) => g + 1);
    return () => {
      m.remove();
      map.current = null;
      loaded.current = false;
    };
  }, [base]);

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
  }, [boundaries, changes, fit, pins, generation]);

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
  }, [pins, generation]);

  return <div ref={ref} style={{ height, width: "100%" }} data-testid={testId} />;
}
