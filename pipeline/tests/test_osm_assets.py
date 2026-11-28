"""OSM asset builder: name normalisation, geometry assembly and an offline rebuild from the saved response."""
import json
from pathlib import Path

from lake_protect.osm_assets import build, element_geometry, normalise

ROOT = Path(__file__).resolve().parents[2]


def test_normalise_collapses_punctuation():
    assert normalise("Bum-Rukn-ud-Daula  Lake") == "bum rukn ud daula lake"


def test_closed_way_becomes_polygon_and_open_way_is_skipped():
    ring = [{"lon": 78.0, "lat": 17.0}, {"lon": 78.01, "lat": 17.0}, {"lon": 78.01, "lat": 17.01}, {"lon": 78.0, "lat": 17.0}]
    assert element_geometry({"type": "way", "geometry": ring}).geom_type == "Polygon"
    assert element_geometry({"type": "way", "geometry": ring[:-1]}) is None


def test_relation_with_inner_ring_has_a_hole():
    outer = [{"lon": x, "lat": y} for x, y in [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]]
    inner = [{"lon": x, "lat": y} for x, y in [(0.4, 0.4), (0.6, 0.4), (0.6, 0.6), (0.4, 0.6), (0.4, 0.4)]]
    rel = {"type": "relation", "members": [{"type": "way", "role": "outer", "geometry": outer}, {"type": "way", "role": "inner", "geometry": inner}]}
    geom = element_geometry(rel)
    assert geom.geom_type == "MultiPolygon" and abs(geom.area - 0.96) < 1e-9


def test_rebuild_from_saved_response_matches_committed_file(tmp_path):
    out = tmp_path / "assets.geojson"
    build(ROOT / "data/case_lake_search.yml", ROOT / "data/sources/overpass_water_orr.json", out, refetch=False)
    # As `lp assets-osm` does: districts and mandals from the saved boundaries (D-060), villages from
    # the saved places (D-069).
    from lake_protect.osm_areas import run as place_areas

    areas_out = tmp_path / "admin_orr.geojson"
    place_areas(out, ROOT / "data/sources/overpass_admin_orr.json", [78.22, 17.20, 78.72, 17.62], refetch=False, areas_out=areas_out,
                places_raw=ROOT / "data/sources/overpass_places_orr.json")
    rebuilt = json.loads(out.read_text(encoding="utf-8"))
    # The district and mandal outlines the API uses to place a citizen's pin (D-063) match too.
    assert json.loads(areas_out.read_text(encoding="utf-8"))["features"] == json.loads((ROOT / "data/areas/admin_orr.geojson").read_text(encoding="utf-8"))["features"]
    committed = json.loads((ROOT / "data/assets.geojson").read_text(encoding="utf-8"))
    assert rebuilt["features"] == committed["features"]
    for f in rebuilt["features"]:
        assert f["properties"]["boundary"]["status"] == "derived"
        assert f["properties"]["is_demo"] is False
