/** Distance from a GPS fix to the candidate polygon, in metres (0 when inside). Good to a metre or two at this scale. */
type Ring = number[][];

function polygons(geom: GeoJSON.Geometry): Ring[][] {
  if (geom.type === "Polygon") return [geom.coordinates as Ring[]];
  if (geom.type === "MultiPolygon") return geom.coordinates as Ring[][];
  return [];
}

function inside(x: number, y: number, ring: Ring): boolean {
  let hit = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) hit = !hit;
  }
  return hit;
}

export function distanceToPolygonM(lon: number, lat: number, geom: GeoJSON.Geometry): number {
  const kx = 111_320 * Math.cos((lat * Math.PI) / 180);
  const ky = 111_320;
  let best = Infinity;
  for (const poly of polygons(geom)) {
    const outer = poly[0];
    if (inside(lon, lat, outer) && !poly.slice(1).some((h) => inside(lon, lat, h))) return 0;
    for (const ring of poly) {
      for (let i = 0; i < ring.length - 1; i++) {
        const ax = (ring[i][0] - lon) * kx, ay = (ring[i][1] - lat) * ky;
        const bx = (ring[i + 1][0] - lon) * kx, by = (ring[i + 1][1] - lat) * ky;
        const dx = bx - ax, dy = by - ay;
        const t = Math.max(0, Math.min(1, -(ax * dx + ay * dy) / (dx * dx + dy * dy || 1)));
        best = Math.min(best, Math.hypot(ax + t * dx, ay + t * dy));
      }
    }
  }
  return best;
}

export function centroidOf(geom: GeoJSON.Geometry): [number, number] {
  const ring = polygons(geom)[0]?.[0] ?? [[0, 0]];
  const n = ring.length - 1 || 1;
  let x = 0, y = 0;
  for (let i = 0; i < n; i++) {
    x += ring[i][0];
    y += ring[i][1];
  }
  return [x / n, y / n];
}

/** Move a point by metres east and north. */
export function offsetM(lon: number, lat: number, east: number, north: number): [number, number] {
  return [lon + east / (111_320 * Math.cos((lat * Math.PI) / 180)), lat + north / 111_320];
}

export function tilesAround(lon: number, lat: number, zooms = [14, 15, 16, 17]): string[] {
  const out: string[] = [];
  for (const z of zooms) {
    const n = 2 ** z;
    const x = Math.floor(((lon + 180) / 360) * n);
    const r = (lat * Math.PI) / 180;
    const y = Math.floor(((1 - Math.asinh(Math.tan(r)) / Math.PI) / 2) * n);
    for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) out.push(`/api/tiles/demo/${z}/${x + dx}/${y + dy}.png`);
  }
  return out;
}
