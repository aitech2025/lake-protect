"""Placing real lakes in their district and mandal from OpenStreetMap boundaries (D-060)."""
from lake_protect.osm_areas import AREA_SOURCE, areas, clean_name, place


def _square_relation(rel_id: int, level: str, name: str, w: float, s: float, e: float, n: float) -> dict:
    ring = [{"lon": w, "lat": s}, {"lon": e, "lat": s}, {"lon": e, "lat": n}, {"lon": w, "lat": n}, {"lon": w, "lat": s}]
    # Two ways that join into one ring, as OSM relations usually do.
    return {
        "type": "relation", "id": rel_id,
        "tags": {"boundary": "administrative", "admin_level": level, "name": name},
        "members": [{"type": "way", "role": "outer", "geometry": ring[:3]}, {"type": "way", "role": "outer", "geometry": ring[2:]}],
    }


def _lake(key: str, lon: float, lat: float) -> dict:
    d = 0.001
    return {"type": "Feature", "properties": {"asset_key": key},
            "geometry": {"type": "Polygon", "coordinates": [[[lon - d, lat - d], [lon + d, lat - d], [lon + d, lat + d], [lon - d, lat + d], [lon - d, lat - d]]]}}


PAYLOAD = {"response": {"elements": [
    _square_relation(1, "5", "Test District", 0.0, 0.0, 2.0, 2.0),
    _square_relation(2, "6", "East mandal", 1.0, 0.0, 2.0, 2.0),
    _square_relation(3, "6", "West Mandal", 0.0, 0.0, 1.0, 2.0),
    {"type": "relation", "id": 4, "tags": {"admin_level": "8", "name": "Ward"}, "members": []},
]}}


def test_mandal_suffix_is_dropped_but_district_names_are_kept():
    assert clean_name("Kapra mandal", "6") == "Kapra"
    assert clean_name("Turkapalle (M) mandal", "6") == "Turkapalle (M)"
    assert clean_name("Medchal–Malkajgiri", "5") == "Medchal–Malkajgiri"


def test_each_lake_takes_the_boundaries_holding_a_point_on_it():
    found = areas(PAYLOAD)
    assert sorted((a["level"], a["name"]) for a in found) == [("district", "Test District"), ("mandal", "East"), ("mandal", "West")]
    features = [_lake("east", 1.5, 1.0), _lake("west", 0.5, 1.0), _lake("away", 5.0, 5.0)]
    out = place(features, found)
    assert out == {"district": 2, "mandal": 2, "unplaced": ["away"]}
    east, west, away = (f["properties"] for f in features)
    assert (east["district"], east["mandal"], east["area_source"]) == ("Test District", "East", AREA_SOURCE)
    assert west["mandal"] == "West"
    assert "district" not in away and away["area_source"] is None
