// Minimal GeoJSON types, so the app does not depend on @types/geojson being hoisted.
declare namespace GeoJSON {
  type Position = number[];
  interface Geometry {
    type: string;
    coordinates: unknown;
  }
  interface Polygon extends Geometry {
    type: "Polygon";
    coordinates: Position[][];
  }
  interface MultiPolygon extends Geometry {
    type: "MultiPolygon";
    coordinates: Position[][][];
  }
  interface Feature {
    type: "Feature";
    geometry: Geometry;
    properties: Record<string, unknown>;
    id?: string | number;
  }
  interface FeatureCollection {
    type: "FeatureCollection";
    features: Feature[];
  }
}
