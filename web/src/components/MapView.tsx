import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState, type RefObject } from "react";
import { createPortal } from "react-dom";
import { useTranslation } from "react-i18next";
import { Focus } from "lucide-react";
import { API_BASE } from "../api";
import { HYDERABAD, SATELLITE, worldStyle } from "./worldStyle";

export type Pin = { id: number | string; lon: number; lat: number; colour: string; label?: string; big?: boolean; onClick?: () => void };

type Box = [number, number, number, number];
type Padding = { top: number; right: number; bottom: number; left: number };

type Props = {
  boundaries?: GeoJSON.FeatureCollection; // features with properties.kind and properties.status
  changes?: GeoJSON.FeatureCollection;
  pins?: Pin[];
  fit?: Box | null;
  height?: string;
  testId?: string;
  /** Drawing an outline (D-061): the corners placed so far, whether it is closed, and a click handler. */
  draft?: [number, number][];
  draftClosed?: boolean;
  onMapClick?: (lngLat: [number, number]) => void;
  /**
   * The world map (D-068): a street map on a globe that opens fitted to the locations (Hyderabad
   * when there are none) and zooms out to Telangana, India and the Earth.
   */
  world?: boolean;
  /** Panels drawn over the map (heading, legend, note): a world map fits the locations clear of them. */
  avoid?: RefObject<HTMLElement | null>[];
};

const EMPTY: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };
const CONFIRMED = ["physically_marked", "final_notification", "surveyed_agency"];
const BASE_KEY = "lp.basemap";

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
      { id: "bg", type: "background", paint: { "background-color": "#17293b" } },
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

function bboxOf(fcs: GeoJSON.FeatureCollection[]): Box | null {
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

const uniform = (n: number): Padding => ({ top: n, right: n, bottom: n, left: n });

/**
 * The ways to keep each panel over the map clear of the fitted box: beside it, or above or below
 * it. The map's own buttons count as a panel.
 */
function clearances(container: HTMLElement, panels: HTMLElement[]): Padding[] {
  const box = container.getBoundingClientRect();
  const gap = 12;
  let options: Padding[] = [uniform(28)];
  for (const el of panels) {
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height || r.right <= box.left || r.left >= box.right || r.bottom <= box.top || r.top >= box.bottom) continue;
    const side: [keyof Padding, number] = r.left - box.left <= box.right - r.right ? ["left", r.right - box.left + gap] : ["right", box.right - r.left + gap];
    const end: [keyof Padding, number] = r.top - box.top <= box.bottom - r.bottom ? ["top", r.bottom - box.top + gap] : ["bottom", box.bottom - r.top + gap];
    options = options.flatMap((o) => [side, end].map(([k, n]) => ({ ...o, [k]: Math.max(o[k], n) })));
  }
  return options;
}

/** MapLibre refuses a fit whose padding leaves no room; shrink it to leave at least a third of the map. */
function roomFor(m: maplibregl.Map, p: Padding): Padding {
  const { clientWidth: w, clientHeight: h } = m.getContainer();
  const sx = Math.min(1, (w * 2) / 3 / Math.max(1, p.left + p.right));
  const sy = Math.min(1, (h * 2) / 3 / Math.max(1, p.top + p.bottom));
  return { top: p.top * sy, right: p.right * sx, bottom: p.bottom * sy, left: p.left * sx };
}

function savedBase(): boolean {
  try {
    return localStorage.getItem(BASE_KEY) === "satellite";
  } catch {
    return false;
  }
}

export function MapView({ boundaries = EMPTY, changes = EMPTY, pins = [], fit, height = "100%", testId, draft, draftClosed = false, onMapClick, world = false, avoid }: Props) {
  const { t } = useTranslation();
  const ref = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const clickRef = useRef(onMapClick);
  clickRef.current = onMapClick;
  const avoidRef = useRef(avoid);
  avoidRef.current = avoid;
  const markers = useRef<maplibregl.Marker[]>([]);
  const loaded = useRef(false);
  const [generation, setGeneration] = useState(0);
  // The world map: whether the online street map loaded, and the viewer's Map/Satellite choice.
  const [online, setOnline] = useState(false);
  const [satellite, setSatellite] = useState(() => world && savedBase());
  const [tools] = useState(() => {
    const el = document.createElement("div");
    el.className = "maplibregl-ctrl map-tools";
    return el;
  });
  // The last box fitted, kept so the map can fit it again on resize or on the fit button.
  const target = useRef<{ box: Box; padding: number; maxZoom: number } | null>(null);
  const moved = useRef(false);

  /** Fit a box; a world map picks the padding that keeps every panel clear and shows it largest. */
  const fitTo = (m: maplibregl.Map, duration = 0) => {
    const f = target.current;
    if (!f) return;
    let padding: Padding = uniform(f.padding);
    if (world) {
      const panels = [m.getContainer().querySelector<HTMLElement>(".maplibregl-ctrl-top-right"), ...(avoidRef.current ?? []).map((r) => r.current)].filter((el): el is HTMLElement => !!el);
      let best = -Infinity;
      for (const option of clearances(m.getContainer(), panels).map((o) => roomFor(m, o))) {
        const zoom = m.cameraForBounds(f.box, { padding: option, maxZoom: f.maxZoom })?.zoom ?? -Infinity;
        if (zoom > best) { best = zoom; padding = option; }
      }
    }
    m.fitBounds(f.box, { padding, duration, maxZoom: f.maxZoom });
  };

  useEffect(() => {
    const container = ref.current;
    if (!container) return;
    let m: maplibregl.Map | null = null;
    let observer: ResizeObserver | null = null;
    let cancelled = false;
    const start = (style: maplibregl.StyleSpecification) => {
      if (cancelled) return;
      const mm = new maplibregl.Map({
        container, style, attributionControl: { compact: true }, maxZoom: 18,
        ...(world ? { bounds: HYDERABAD, fitBoundsOptions: { padding: 28 } } : { center: CENTRE, zoom: 10 }),
      });
      m = mm;
      mm.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
      if (world) mm.addControl({ onAdd: () => tools, onRemove: () => tools.remove() }, "top-right");
      mm.on("load", () => {
        mm.addSource("boundaries", { type: "geojson", data: EMPTY });
        mm.addSource("changes", { type: "geojson", data: EMPTY });
        const isKind = (k: string[]) => ["in", ["get", "kind"], ["literal", k]] as maplibregl.ExpressionSpecification;
        mm.addLayer({ id: "ring", type: "line", source: "boundaries", filter: isKind(["watch_ring"]), paint: { "line-color": "#8292a3", "line-width": 1.2, "line-dasharray": [1, 3] } });
        mm.addLayer({ id: "buffer", type: "line", source: "boundaries", filter: isKind(["buffer"]), paint: { "line-color": "#c94b4b", "line-width": 1.6, "line-dasharray": [3, 2] } });
        const primary = ["ftl", "parcel"];
        const certaintyIs = (c: string) => ["all", isKind(primary), ["==", ["get", "certainty"], c]] as maplibregl.FilterSpecification;
        mm.addLayer({ id: "primary-fill", type: "fill", source: "boundaries", filter: isKind(primary), paint: { "fill-color": "#167c80", "fill-opacity": 0.08 } });
        mm.addLayer({ id: "primary-confirmed", type: "line", source: "boundaries", filter: certaintyIs("confirmed"), paint: { "line-color": "#167c80", "line-width": 2.6 } });
        mm.addLayer({ id: "primary-preliminary", type: "line", source: "boundaries", filter: certaintyIs("preliminary"), paint: { "line-color": "#d69b32", "line-width": 2.6, "line-dasharray": [3, 2] } });
        mm.addLayer({ id: "primary-estimated", type: "line", source: "boundaries", filter: certaintyIs("estimated"), paint: { "line-color": "#8292a3", "line-width": 2.6, "line-dasharray": [0.6, 2] } });
        mm.addLayer({ id: "change-fill", type: "fill", source: "changes", paint: { "fill-color": "#d69b32", "fill-opacity": 0.55 } });
        mm.addLayer({ id: "change-line", type: "line", source: "changes", paint: { "line-color": "#74500f", "line-width": 1.6 } });
        mm.addSource("draft", { type: "geojson", data: EMPTY });
        mm.addLayer({ id: "draft-fill", type: "fill", source: "draft", filter: ["==", ["geometry-type"], "Polygon"], paint: { "fill-color": "#d69b32", "fill-opacity": 0.25 } });
        mm.addLayer({ id: "draft-line", type: "line", source: "draft", filter: ["!=", ["geometry-type"], "Point"], paint: { "line-color": "#d69b32", "line-width": 2.4 } });
        mm.addLayer({ id: "draft-points", type: "circle", source: "draft", filter: ["==", ["geometry-type"], "Point"], paint: { "circle-radius": 5, "circle-color": "#ffffff", "circle-stroke-color": "#74500f", "circle-stroke-width": 2 } });
        loaded.current = true;
        mm.fire("lp:data");
      });
      mm.on("click", (e) => clickRef.current?.([Number(e.lngLat.lng.toFixed(6)), Number(e.lngLat.lat.toFixed(6))]));
      // A drag, scroll or button press by the viewer: from then on a resize keeps their view.
      mm.on("movestart", (e: { originalEvent?: Event }) => {
        if (e.originalEvent) moved.current = true;
      });
      map.current = mm;
      setGeneration((g) => g + 1);
      // The container can change size without the window resizing (sidebar, panels, layout), so follow
      // it; a world map the viewer has not moved fits its locations again.
      observer = new ResizeObserver(() => {
        mm.resize();
        if (world && !moved.current) fitTo(mm);
      });
      observer.observe(container);
    };
    if (world) {
      void worldStyle().then((w) => {
        if (cancelled) return;
        setOnline(w.online);
        start(w.style);
      });
    } else start(STYLE);
    return () => {
      cancelled = true;
      observer?.disconnect();
      m?.remove();
      map.current = null;
      loaded.current = false;
    };
    // The map is made once; `world` and `tools` do not change for a mounted map.
  }, []);

  useEffect(() => {
    const m = map.current;
    if (!m) return;
    const apply = () => {
      (m.getSource("boundaries") as maplibregl.GeoJSONSource | undefined)?.setData(withCertainty(boundaries) as never);
      (m.getSource("changes") as maplibregl.GeoJSONSource | undefined)?.setData(changes as never);
      const shapes = fit ?? bboxOf([boundaries, changes]);
      const pinBox = pins.length ? bboxOf([{ type: "FeatureCollection", features: pins.map((p) => ({ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [p.lon, p.lat] } })) }]) : null;
      // Pins alone stay at district scale; shapes may zoom in to street level. A world map with
      // nothing to show opens on Hyderabad.
      target.current = shapes ? { box: shapes, padding: 48, maxZoom: 16.5 }
        : pinBox ? { box: pinBox, padding: 60, maxZoom: 14 }
        : world ? { box: HYDERABAD, padding: 28, maxZoom: 14 }
        : null;
      moved.current = false;
      fitTo(m);
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
    if (!m || !world || !online) return;
    const apply = () => {
      if (m.getLayer(SATELLITE)) m.setLayoutProperty(SATELLITE, "visibility", satellite ? "visible" : "none");
    };
    if (loaded.current) apply();
    else m.once("lp:data", apply);
    try {
      localStorage.setItem(BASE_KEY, satellite ? "satellite" : "map");
    } catch {
      /* storage blocked: the choice lasts for this page only */
    }
  }, [satellite, online, world, generation]);

  useEffect(() => {
    const m = map.current;
    if (!m) return;
    // Many names on one map overlap; past a handful they appear on hover and focus instead.
    ref.current?.classList.toggle("many-labels", pins.filter((p) => p.big && p.label).length > 6);
    markers.current.forEach((mk) => mk.remove());
    markers.current = pins.map((p) => {
      const el = document.createElement("button");
      el.type = "button";
      el.className = "pin-wrap";
      el.dataset.assetId = String(p.id);
      el.setAttribute("aria-label", p.label ?? String(p.id));
      if (p.onClick) el.addEventListener("click", p.onClick);
      const dot = document.createElement("span");
      dot.className = `pin${p.big ? " big" : ""}`;
      dot.style.background = p.colour;
      dot.setAttribute("aria-hidden", "true");
      el.appendChild(dot);
      if (p.label && p.big) {
        const label = document.createElement("div");
        label.className = "pin-label";
        label.textContent = p.label;
        el.appendChild(label);
      }
      const marker = new maplibregl.Marker({ element: el, anchor: "center" }).setLngLat([p.lon, p.lat]).addTo(m);
      marker.getElement().setAttribute("aria-label", p.label ?? String(p.id));
      marker.getElement().dataset.assetId = String(p.id);
      return marker;
    });
  }, [pins, generation]);

  const refit = () => {
    const m = map.current;
    if (!m) return;
    moved.current = false;
    fitTo(m, 900);
  };

  return (
    <>
      <div ref={ref} className={world ? "world-map" : undefined} style={{ height, width: "100%" }} data-testid={testId} />
      {world && createPortal(
        <>
          <div className="maplibregl-ctrl-group">
            <button type="button" onClick={refit} title={t("map.fit")} aria-label={t("map.fit")} data-testid="map-fit">
              <Focus size={16} aria-hidden="true" />
            </button>
          </div>
          {online && (
            <div className="maplibregl-ctrl-group map-base" role="group" aria-label={t("map.base")}>
              {(["map", "satellite"] as const).map((b) => (
                <button key={b} type="button" aria-pressed={(b === "satellite") === satellite} onClick={() => setSatellite(b === "satellite")} data-testid={`map-base-${b}`}>
                  {t(`map.base_${b}`)}
                </button>
              ))}
            </div>
          )}
        </>,
        tools,
      )}
    </>
  );
}
