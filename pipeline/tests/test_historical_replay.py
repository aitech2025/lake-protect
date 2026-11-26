import datetime as dt
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from shapely.geometry import box, mapping

from lake_protect.replay import ReplayError, run_replay, weekly_dates


def _aoi():
    return SimpleNamespace(
        asset_id=7,
        asset_key="lake-7",
        baseline_date=dt.date(2020, 1, 1),
        primary_ll=box(78.0, 17.0, 78.01, 17.01),
    )


def _fake_run(calls):
    def execute(aois, as_of, **kwargs):
        calls.append(as_of)
        candidate = {
            "asset_key": "lake-7",
            "asset_id": 7,
            "change_type": "soil_fill",
            "first_changed_at": "2024-01-03",
            "area_sq_m": 1250.0,
            "geometry": mapping(box(78.001, 17.001, 78.002, 17.002)),
        }
        return [SimpleNamespace(aoi=aois[0], candidates=[candidate])], {
            "as_of": as_of.isoformat(), "rule_version": "test-v1", "rules_sha256": "a" * 64,
        }
    return execute


def _fake_writer(results, meta, folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    features = []
    for result in results:
        for candidate in result.candidates:
            properties = {k: v for k, v in candidate.items() if k != "geometry"}
            features.append({"type": "Feature", "geometry": candidate["geometry"], "properties": properties})
    (folder / "candidates.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8"
    )
    return folder


def test_weekly_dates_include_requested_end_date():
    assert weekly_dates(dt.date(2024, 1, 1), dt.date(2024, 1, 16)) == [
        dt.date(2024, 1, 1), dt.date(2024, 1, 8), dt.date(2024, 1, 15), dt.date(2024, 1, 16)
    ]


@pytest.mark.parametrize(
    "start,end,step",
    [
        (dt.date(2024, 2, 1), dt.date(2024, 1, 1), 7),
        (dt.date(2024, 1, 1), dt.date(2024, 1, 2), 0),
    ],
)
def test_weekly_dates_reject_invalid_ranges(start, end, step):
    with pytest.raises(ValueError):
        weekly_dates(start, end, step)


def test_replay_deduplicates_candidates_and_keeps_first_detection_date(tmp_path):
    calls = []
    result = run_replay(
        [_aoi()],
        start=dt.date(2024, 1, 1),
        end=dt.date(2024, 1, 15),
        out_dir=tmp_path / "replay",
        screen_run=_fake_run(calls),
        report_writer=_fake_writer,
        log=lambda *_: None,
    )

    assert calls == [dt.date(2024, 1, 1), dt.date(2024, 1, 8), dt.date(2024, 1, 15)]
    assert result["status"] == "complete"
    assert result["completed_dates"] == ["2024-01-01", "2024-01-08", "2024-01-15"]
    assert result["detections"] == 1

    data = json.loads((tmp_path / "replay" / "detections.geojson").read_text())
    assert len(data["features"]) == 1
    feature = data["features"][0]
    assert feature["properties"]["detected_at"] == "2024-01-01"
    assert feature["properties"]["geometry_crs"] == "EPSG:4326"
    assert feature["properties"]["first_changed_at"] == "2024-01-03"
    assert feature["properties"]["replay_as_of"] == "2024-01-01"


def test_replay_resumes_completed_weeks_without_rerunning_detector(tmp_path):
    calls = []
    kwargs = dict(
        start=dt.date(2024, 1, 1), end=dt.date(2024, 1, 8),
        out_dir=tmp_path / "replay", screen_run=_fake_run(calls),
        report_writer=_fake_writer, log=lambda *_: None,
    )
    run_replay([_aoi()], **kwargs)
    assert len(calls) == 2

    run_replay([_aoi()], **kwargs)
    assert len(calls) == 2


def test_replay_refuses_to_mix_different_dates_or_aoi_snapshot(tmp_path):
    calls = []
    out = tmp_path / "replay"
    run_replay(
        [_aoi()], start=dt.date(2024, 1, 1), end=dt.date(2024, 1, 8),
        out_dir=out, screen_run=_fake_run(calls), report_writer=_fake_writer, log=lambda *_: None,
    )
    with pytest.raises(ReplayError, match="inputs or detector rules differ"):
        run_replay(
            [_aoi()], start=dt.date(2024, 1, 1), end=dt.date(2024, 1, 15),
            out_dir=out, screen_run=_fake_run(calls), report_writer=_fake_writer, log=lambda *_: None,
        )


def test_replay_requires_at_least_one_asset(tmp_path):
    with pytest.raises(ValueError, match="at least one AOI"):
        run_replay(
            [], start=dt.date(2024, 1, 1), end=dt.date(2024, 1, 8),
            out_dir=tmp_path / "empty", screen_run=_fake_run([]), report_writer=_fake_writer,
        )
