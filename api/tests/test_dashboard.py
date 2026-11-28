"""The drill-down dashboard (DECISIONS.md D-060): State, district, mandal, village, asset, seen within
each persona's scope (D-067)."""
from __future__ import annotations

import datetime as dt
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.models import AssetScreen, Notification, ScreenRun
from app.services import dashboard
from tests.factories import auth, cover, decide, ingest, make_asset, make_user, review

NOW = dt.datetime(2025, 7, 10, 6, tzinfo=dt.timezone.utc)  # 2025-W28


@pytest.fixture()
def d(db):
    admin = make_user(db, "admin")
    senior = make_user(db, "senior_official")
    official = make_user(db, "district_officer")
    cover(db, official, "North")
    a = SimpleNamespace(
        v1=make_asset(db, district="North", mandal="Mandal A", village="Village 1"),
        v2=make_asset(db, district="North", mandal="Mandal A", village="Village 2"),
        b=make_asset(db, district="North", mandal="Mandal B"),  # no village recorded
        s=make_asset(db, district="South", mandal="Mandal C", village="Village 3", cohort="D_UNNOTIFIED"),
        x=make_asset(db, district=None),  # no area at all
    )
    t = dt.datetime(2025, 6, 20, 6, tzinfo=dt.timezone.utc)
    _, waiting = ingest(db, a.v1, at=t)  # open since 20 Jun: waiting more than 14 days by 10 Jul
    _, reviewed = ingest(db, a.b, at=NOW - dt.timedelta(days=2))
    review(db, reviewed, official, at=NOW - dt.timedelta(days=1))
    _, confirmed = ingest(db, a.s, at=NOW - dt.timedelta(days=3))
    decide(db, confirmed, senior, to="CONFIRMED", at=NOW - dt.timedelta(days=2))  # no district officer covers South
    legacy, _ = ingest(db, a.v2, at=NOW - dt.timedelta(days=1), first_changed=dt.date(2024, 12, 1), last_clear=dt.date(2024, 11, 25))
    assert legacy["outcome"] == "closed_by_legal_check"
    for week, as_of, status in (("2025-W27", dt.date(2025, 7, 2), "no_candidate"), ("2025-W28", dt.date(2025, 7, 9), "candidate_found")):
        run = ScreenRun(as_of=as_of, rule_version="t", rules_sha256="a" * 64, collection="test", started_at=NOW, finished_at=NOW,
                        assets_total=5, outcomes={}, is_demo=True)
        db.add(run)
        db.flush()
        for asset in (a.v1, a.v2, a.b, a.s, a.x):
            st = "no_usable_look" if asset is a.x else (status if asset is a.v1 else "no_candidate")
            db.add(AssetScreen(run_id=run.id, asset_id=asset.id, status=st, looks=1, candidates=0, legacy_changes=0, counts={}, week=week, changes=[]))
    db.flush()
    return SimpleNamespace(admin=admin, senior=senior, official=official, a=a, waiting=waiting, reviewed=reviewed, confirmed=confirmed)


def view(db, user, **path):
    return dashboard.overview(db, user, now=NOW, **path)


def test_the_state_level_counts_everything_and_groups_by_district(db, d):
    out = view(db, d.senior)
    f = out["figures"]
    assert (out["level"], out["child_level"], out["week"]) == ("state", "district", "2025-W28")
    assert f["assets"] == 5 and f["clear_look"] == 4 and f["no_clear_look"] == 1 and f["changed"] == 1
    assert (f["open"], f["under_review"], f["confirmed"], f["waiting"]) == (1, 1, 1, 1)
    assert f["new_incidents"] == 2  # created in 2025-W28, not counting the one the legal check closed at once
    assert [c["name"] for c in out["children"]] == ["North", "South", "-"]
    assert sum(c["figures"]["assets"] for c in out["children"]) == 5
    assert out["children"][2]["not_recorded"] and out["children"][2]["params"] == {"district": "-"}
    assert {c["name"]: c["tone"] for c in out["children"]} == {"North": "waiting", "South": "quiet", "-": "no_look"}
    assert out["my_areas"] == [] and view(db, d.official)["my_areas"] == [{"district": "North", "mandal": None}]
    assert [t["week"] for t in out["trend"]] == ["2025-W27", "2025-W28"]
    assert out["trend"][1]["changed"] == 1 and out["trend"][0]["changed"] == 0


def test_drilling_down_by_mandal_village_and_skipping_a_missing_level(db, d):
    north = view(db, d.official, district="North")
    assert [c["name"] for c in north["children"]] == ["Mandal A", "Mandal B"]
    assert [p["name"] for p in north["path"]] == ["Telangana", "North"]
    mandal_a = view(db, d.official, district="North", mandal="mandal a")  # case does not matter
    assert mandal_a["child_level"] == "village" and [c["name"] for c in mandal_a["children"]] == ["Village 1", "Village 2"]
    mandal_b = view(db, d.official, district="North", mandal="Mandal B")
    assert mandal_b["child_level"] == "asset"
    assert [c["asset_id"] for c in mandal_b["children"]] == [d.a.b.id]
    village = view(db, d.official, district="North", mandal="Mandal A", village="Village 1")
    row = village["children"][0]
    assert (row["kind"], row["asset_id"], row["week_status"], row["tone"]) == ("asset", d.a.v1.id, "candidate_found", "waiting")
    assert [p["level"] for p in village["path"]] == ["state", "district", "mandal", "village"]


def test_acknowledged_within_24_hours(db, d):
    notes = db.scalars(select(Notification).where(Notification.user_id == d.official.id, Notification.kind == "incident_opened")).all()
    # The waiting incident was never acknowledged; the reviewed one was, within a day.
    assert len(notes) == 2
    f = view(db, d.official)["figures"]
    assert (f["ack_on_time"], f["ack_considered"]) == (1, 2)


def test_every_number_opens_the_same_incidents(client, db, d, monkeypatch):
    monkeypatch.setattr("app.routers.alerts.utcnow", lambda: NOW)
    monkeypatch.setattr("app.routers.dashboard.utcnow", lambda: NOW)
    out = client.get("/dashboard", headers=auth(d.senior)).json()
    for child in out["children"]:
        q = "&".join(f"{k}={v}" for k, v in child["params"].items())
        listed = client.get(f"/alerts?state=OPEN,UNDER_REVIEW,FIELD_VISIT,FIELD_REPORTED&{q}", headers=auth(d.senior)).json()["count"]
        assert listed == child["figures"]["open"] + child["figures"]["under_review"], child["name"]
        waiting = client.get(f"/alerts?waiting=true&{q}", headers=auth(d.senior)).json()["count"]
        assert waiting == child["figures"]["waiting"], child["name"]
    assert client.get("/dashboard?mandal=Mandal A", headers=auth(d.official)).status_code == 422
    assert client.get("/dashboard?district=North&mandal=Mandal A", headers=auth(d.admin)).json()["level"] == "mandal"


def test_a_stopped_location_no_longer_counts_as_watched_but_its_incidents_still_show(db, d):
    from app.models import MonitoringChange

    for asset in (d.a.v1, d.a.x):  # v1 has an incident waiting; x has none
        db.add(MonitoringChange(asset_id=asset.id, monitored=False, reason="Test stop", actor_id=d.admin.id))
    db.flush()
    out = view(db, d.senior)
    f = out["figures"]
    assert f["assets"] == 3 and f["no_clear_look"] == 0 and f["changed"] == 0
    assert f["open"] == 1 and f["waiting"] == 1  # the incident on v1 still needs a decision
    assert [c["name"] for c in out["children"]] == ["North", "South"]  # x had nothing left to show
    rows = {c["name"]: c for c in view(db, d.official, district="North", mandal="Mandal A")["children"]}
    v1 = view(db, d.official, district="North", mandal="Mandal A", village="Village 1")["children"][0]
    assert v1["monitored"] is False and v1["category"] == "water_body" and rows["Village 1"]["figures"]["assets"] == 0
    assert {c["name"]: c["watched"] for c in out["by_category"]} == {"water_body": 3, "government_land": 0, "endowment_land": 0, "forest_land": 0}


def test_a_district_officer_sees_only_their_area_and_a_field_officer_only_their_visits(db, d):
    out = view(db, d.official)
    assert [c["name"] for c in out["children"]] == ["North"]  # their district only
    assert out["figures"]["assets"] == 3 and out["figures"]["confirmed"] == 0
    field = make_user(db, "field_officer")
    cover(db, field, "North")
    assert view(db, field)["figures"]["assets"] == 0
    from app.workflow import incidents

    incidents.assign(db, d.waiting, d.official, field.id, "Visit", at=NOW)
    seen = view(db, field)
    assert seen["figures"]["assets"] == 1 and [p["asset_id"] for p in seen["pins"]] == [d.a.v1.id]
