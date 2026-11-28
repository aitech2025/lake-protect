import type { ExpressionSpecification, FilterSpecification, LayerSpecification, SourceSpecification, StyleSpecification } from "maplibre-gl";
import { API_BASE } from "../api";

/**
 * The world map behind the Map and Overview pages (D-068): a street map on a globe that opens on
 * the watched locations in Hyderabad and zooms out to Telangana, India and the Earth.
 *
 * Online it is OpenFreeMap's OpenStreetMap style, with labels in Latin script, India's own view of
 * its borders, the Telangana outline and an optional satellite layer. With no internet, or with
 * LP_BASEMAP_STYLE=offline at build time, it falls back to local files only: country shapes, the
 * same borders and outline, and the Sentinel-2 tiles of the watched area (D-047).
 */

/** The watched area: the Outer Ring Road box the Sentinel-2 base map covers (pipeline/lake_protect/basemap.py). */
export const HYDERABAD: [number, number, number, number] = [78.22, 17.2, 78.72, 17.62];
/** Layer id of the Sentinel-2 tiles, which the Map/Satellite switch shows or hides. */
export const SATELLITE = "lp-satellite";

const DEFAULT_STYLE = "https://tiles.openfreemap.org/styles/liberty";
const setting = String(import.meta.env.VITE_LP_BASEMAP_STYLE ?? "").trim();
const ONLINE_STYLE: string | null = setting === "" ? DEFAULT_STYLE : setting === "offline" ? null : setting;

const ACCENT = "#1d4f91";
const local = (path: string) => new URL(path, window.location.origin).href;

// Labels in Latin script only: the map renderer cannot join Telugu or other Indic letters.
const LATIN: ExpressionSpecification = ["coalesce", ["get", "name_en"], ["get", "name:latin"], ["get", "name"]];

const GLOBE: Pick<StyleSpecification, "projection" | "sky"> = {
  projection: { type: "globe" },
  sky: { "atmosphere-blend": ["interpolate", ["linear"], ["zoom"], 0, 1, 5, 1, 7, 0] },
};

function contextSources(): Record<string, SourceSpecification> {
  return {
    "lp-borders": { type: "geojson", data: local("/context/borders.geojson") },
    "lp-telangana": { type: "geojson", data: local("/context/telangana.geojson") },
    "lp-s2": {
      type: "raster",
      tiles: [`${API_BASE}/tiles/s2/{z}/{x}/{y}.jpg`],
      tileSize: 256,
      minzoom: 9,
      maxzoom: 14,
      bounds: HYDERABAD,
      attribution: "Sentinel-2: contains modified Copernicus data",
    },
  };
}

function contextLayers(satelliteVisible: boolean): LayerSpecification[] {
  return [
    { id: SATELLITE, type: "raster", source: "lp-s2", layout: { visibility: satelliteVisible ? "visible" : "none" } },
    {
      id: "lp-borders",
      type: "line",
      source: "lp-borders",
      layout: { "line-join": "round", "line-cap": "round" },
      paint: {
        "line-color": "#62666e",
        "line-opacity": ["interpolate", ["linear"], ["zoom"], 0, 0.45, 4, 1],
        "line-width": ["interpolate", ["linear"], ["zoom"], 1, 0.6, 4, 1.1, 8, 1.8],
      },
    },
    {
      id: "lp-telangana-tint",
      type: "fill",
      source: "lp-telangana",
      maxzoom: 9,
      paint: { "fill-color": ACCENT, "fill-opacity": ["interpolate", ["linear"], ["zoom"], 3, 0.2, 6, 0.1, 9, 0] },
    },
    {
      id: "lp-telangana-casing",
      type: "line",
      source: "lp-telangana",
      layout: { "line-join": "round" },
      paint: { "line-color": "#ffffff", "line-opacity": 0.85, "line-width": ["interpolate", ["linear"], ["zoom"], 3, 3, 8, 5, 12, 6] },
    },
    {
      id: "lp-telangana-line",
      type: "line",
      source: "lp-telangana",
      layout: { "line-join": "round" },
      paint: { "line-color": ACCENT, "line-width": ["interpolate", ["linear"], ["zoom"], 3, 1.2, 8, 2.4, 12, 3] },
    },
  ];
}

/** OpenFreeMap's style, adjusted: Latin labels, India's borders, Telangana, satellite, globe. */
function adjust(style: StyleSpecification): StyleSpecification {
  const layers = style.layers.map((layer): LayerSpecification => {
    if (layer.type === "symbol" && JSON.stringify(layer.layout?.["text-field"] ?? "").includes("name:nonlatin")) {
      return { ...layer, layout: { ...layer.layout, "text-field": LATIN } };
    }
    // National and disputed lines come from India's point of view instead (lp-borders); the tiles
    // carry OpenStreetMap's. State, district and mandal lines stay.
    if (layer.type === "line" && layer["source-layer"] === "boundary") {
      const own: FilterSpecification[] = [[">=", ["to-number", ["get", "admin_level"], 0], 3], ["!=", ["get", "disputed"], 1]];
      return { ...layer, filter: ["all", ...(layer.filter ? [layer.filter] : []), ...own] as FilterSpecification };
    }
    return layer;
  });
  const firstLabel = layers.findIndex((l) => l.type === "symbol");
  layers.splice(firstLabel < 0 ? layers.length : firstLabel, 0, ...contextLayers(false));
  return { ...style, ...GLOBE, sources: { ...style.sources, ...contextSources() }, layers };
}

function offlineStyle(): StyleSpecification {
  return {
    version: 8,
    ...GLOBE,
    sources: { "lp-countries": { type: "geojson", data: local("/context/countries.geojson") }, ...contextSources() },
    layers: [
      { id: "lp-sea", type: "background", paint: { "background-color": "#b9d0e4" } },
      { id: "lp-land", type: "fill", source: "lp-countries", paint: { "fill-color": "#f1efe8" } },
      ...contextLayers(true),
    ],
  };
}

let online: Promise<StyleSpecification> | null = null;

async function fetchStyle(url: string): Promise<StyleSpecification> {
  const abort = new AbortController();
  const timer = window.setTimeout(() => abort.abort(), 4000);
  try {
    // Revalidate, so a cached style is not used when the tiles behind it cannot be reached.
    const response = await fetch(url, { signal: abort.signal, cache: "no-cache" });
    if (!response.ok) throw new Error(`base map style: HTTP ${response.status}`);
    return adjust((await response.json()) as StyleSpecification);
  } finally {
    window.clearTimeout(timer);
  }
}

/** The style for a new world map, and whether it is the online street map. */
export async function worldStyle(): Promise<{ style: StyleSpecification; online: boolean }> {
  if (ONLINE_STYLE) {
    try {
      online ??= fetchStyle(ONLINE_STYLE);
      return { style: structuredClone(await online), online: true };
    } catch {
      online = null; // no internet: the next map tries again
    }
  }
  return { style: offlineStyle(), online: false };
}
