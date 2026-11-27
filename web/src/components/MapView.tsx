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
  /** Drawing an outline (D-061): the corners placed so far, whether it is closed, and a click handler. */
  draft?: [number, number][];
  draftClosed?: boolean;
  onMapClick?: (lngLat: [number, number]) => void;
};

const EMPTY: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };
const CONFIRMED = ["physically_marked", "final_notification", "surveyed_agency"];

// Offline style: local tiles, no glyphs or sprites, so no request leaves the machine. The base map is
// Sentinel-2 at 10 m, made by `lp basemap` (the drawn demo map is removed, D-065). Zoom 14 is the
// finest level made, so closer views enlarge it rather than suggest detail the data does not have.
const STYLE: maplibregl.StyleSpecification = {
    version: 8,
    sources: {
      base: {
        type: "raster",
        tiles: [`${API_BASE}/tiles/s2/{z}/{x}/{y}.jpg`],
        tileSize: 256,
        minzoom: 9,
        maxzoom: 14,
        attribution: "",
      },
    },
    layers: [
      { id: "bg", type: "background", paint: { "background-color": "#262a28" } },
      { id: "base", type: "raster", source: "base" },
    ],
};
const CENTRE: [number, number] = [78.47, 17.41];

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

function draftFc(points: [number, number][], closed: boolean): GeoJSON.FeatureCollection {
  const features: GeoJSON.Feature[] = points.map((p) => ({ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: p } }));
  if (points.length >= 3 && closed) {
    features.push({ type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [[...points, points[0]]] } });
  } else if (points.length >= 2) {
    features.push({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: points } });
  }
  return { type: "FeatureCollection", features };
}

export function MapView({ boundaries = EMPTY, changes = EMPTY, pins = [], fit, height = "100%", testId, draft, draftClosed = false, onMapClick }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const clickRef = useRef(onMapClick);
  clickRef.current = onMapClick;
  const markers = useRef<maplibregl.Marker[]>([]);
  const loaded = useRef(false);
  const [generation, setGeneration] = useState(0);

  useEffect(() => {
    if (!ref.current) return;
    const m = new maplibregl.Map({ container: ref.current, style: STYLE, center: CENTRE, zoom: 10, attributionControl: { compact: true }, maxZoom: 18 });
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
      m.addSource("draft", { type: "geojson", data: EMPTY });
      m.addLayer({ id: "draft-fill", type: "fill", source: "draft", filter: ["==", ["geometry-type"], "Polygon"], paint: { "fill-color": "#e0a526", "fill-opacity": 0.25 } });
      m.addLayer({ id: "draft-line", type: "line", source: "draft", filter: ["!=", ["geometry-type"], "Point"], paint: { "line-color": "#e0a526", "line-width": 2.4 } });
      m.addLayer({ id: "draft-points", type: "circle", source: "draft", filter: ["==", ["geometry-type"], "Point"], paint: { "circle-radius": 5, "circle-color": "#ffffff", "circle-stroke-color": "#7a4f05", "circle-stroke-width": 2 } });
      loaded.current = true;
      m.fire("lp:data");
    });
    m.on("click", (e) => clickRef.current?.([Number(e.lngLat.lng.toFixed(6)), Number(e.lngLat.lat.toFixed(6))]));
    map.current = m;
    setGeneration((g) => g + 1);
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
  }, [boundaries, changes, fit, pins, generation]);

  useEffect(() => {
    const m = map.current;
    if (!m) return;
    const apply = () => {
      (m.getSource("draft") as maplibregl.GeoJSONSource | undefined)?.setData(draftFc(draft ?? [], draftClosed) as never);
      m.getCanvas().style.cursor = onMapClick ? "crosshair" : "";
      if (onMapClick) m.doubleClickZoom.disable();
      else m.doubleClickZoom.enable();
    };
    if (loaded.current) apply();
    else m.once("lp:data", apply);
  }, [draft, draftClosed, onMapClick, generation]);

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
