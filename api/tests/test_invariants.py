"""Invariant tests from CONTEXT.md section 12, as they stand after DECISIONS.md D-057.

Invariants 1, 2, 3 and 5 guarded the officer path, field assignment and two-person closures,
which were removed with those roles; their facts now show on each incident as flags (court
matter, unconfirmed boundary) for the officials and the admin to weigh. Invariants 10, 11 and 13
are tested where their code lives: pipeline/tests, test_wording.py and test_evidence_pack.py.
"""
import datetime as dt

import pytest
from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.models import Alert, Candidate, OwnerClaim, Permit
from app.services import boundaries as bsvc
from app.services import ingest as ingest_svc
from tests.factories import Team, auth, candidate_in, decide, ingest, make_asset, rect, review, square

T0 = dt.datetime(2025, 6, 20, 6, tzinfo=dt.timezone.utc)


# 4 ------------------------------------------------------------------------------------------

def test_invariant_4_candidates_and_incidents_carry_no_owner_fields(db):
    for model in (Candidate, Alert):
        cols = {c.name for c in model.__table__.columns}
        assert not {c for c in cols if "owner_name" in c or "claimant" in c or "encroach" in c}
    payload = candidate_in(make_asset(db)).model_dump()
    payload["owner_name"] = "Someone"
    with pytest.raises(ValueError):
        ingest_svc.CandidateIn.model_validate(payload)


def test_invariant_4_owner_claims_wait_for_a_confirmed_change(db):
    team = Team(db)
    _, alert = ingest(db, make_asset(db), at=T0)
    with pytest.raises(DBAPIError, match="only after the change is confirmed"):
        with db.begin_nested():
            db.add(OwnerClaim(alert_id=alert.id, claim_type="private_title", claimant_name="Test", entered_by=team.admin.id, entered_at=T0))
            db.flush()
    decide(db, alert, team.admin, "CONFIRMED")
    db.add(OwnerClaim(alert_id=alert.id, claim_type="private_title", claimant_name="Test", entered_by=team.admin.id, entered_at=T0))
    db.flush()


# 6 ------------------------------------------------------------------------------------------

@pytest.mark.parametrize("first_changed", [dt.date(2025, 1, 1), dt.date(2024, 11, 3)])
def test_invariant_6_change_on_or_before_baseline_is_closed_at_once(db, first_changed):
    _, alert = ingest(db, make_asset(db), first_changed=first_changed, last_clear=first_changed - dt.timedelta(days=10))
    assert (alert.state, alert.resolution) == ("CLOSED", "auto")


# 7 ------------------------------------------------------------------------------------------

def _permit(db, geometry: dict) -> None:
    from shapely.geometry import shape

    g = shape(geometry)
    db.add(Permit(source="Test", ref="TEST-P", kind="building", valid_from=dt.date(2020, 1, 1), is_demo=True,
                  geom=WKTElement(f"MULTIPOLYGON((({', '.join(f'{x} {y}' for x, y in g.exterior.coords)})))", srid=4326)))
    db.flush()


@pytest.mark.parametrize("geometry", [square(side_m=60), rect(230, 250, -50, 50)])
def test_invariant_7_permit_inside_ftl_or_buffer_never_closes_the_incident(db, geometry):
    asset = make_asset(db, cohort="B_FINAL", geometry=square(side_m=450))
    _permit(db, geometry)
    _, alert = ingest(db, asset, geometry=geometry)
    assert alert.state == "OPEN"
    assert "permit_conflict" in db.scalar(text("SELECT flags FROM legal_checks WHERE candidate_id = :c"), {"c": alert.candidate_id})


def test_invariant_7_control_permit_in_watch_ring_does_close(db):
    asset = make_asset(db, cohort="B_FINAL", geometry=square(side_m=450))
    ring = rect(270, 310, -20, 20)
    _permit(db, ring)
    _, alert = ingest(db, asset, geometry=ring)
    assert (alert.state, alert.resolution) == ("CLOSED", "auto")


# 8 ------------------------------------------------------------------------------------------

def test_invariant_8_water_loss_alone_never_creates_an_incident(db, client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "pipeline_token", "test-token")
    asset = make_asset(db)
    before = db.scalar(select(func.count()).select_from(Alert))
    payload = candidate_in(asset, change_type="water_loss").model_dump(mode="json")
    resp = client.post("/candidates", json=payload, headers={"X-Pipeline-Token": "test-token"})
    assert resp.status_code == 422 and "Water loss" in resp.json()["detail"]
    assert db.scalar(select(func.count()).select_from(Alert)) == before


def test_invariant_8_database_refuses_an_incident_for_water_loss(db):
    asset = make_asset(db)
    primary = bsvc.primary_of(bsvc.current_boundary_set(db, asset.id))
    cand = Candidate(asset_id=asset.id, boundary_id=primary["id"], geom=WKTElement("MULTIPOLYGON(((81.5 14.5, 81.501 14.5, 81.501 14.501, 81.5 14.5)))", srid=4326),
                     area_sq_m=5000, change_type="water_loss", first_changed_at=dt.date(2025, 6, 1), sensor_basis="optical_only", confidence=0.5, rule_version="t", created_at=T0)
    db.add(cand)
    db.flush()
    with pytest.raises(DBAPIError, match="water loss"):
        with db.begin_nested():
            db.add(Alert(code="X-1", candidate_id=cand.id, state="OPEN", created_at=T0, updated_at=T0))
            db.flush()


# 9 ------------------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "tamper",
    [
        "UPDATE audit_log SET details = '{\"tampered\": true}' WHERE id = :i",
        "UPDATE audit_log SET at = at + interval '1 second' WHERE id = :i",
        "UPDATE audit_log SET actor_id = NULL WHERE id = :i",
        "DELETE FROM audit_log WHERE id = :i",
    ],
)
def test_invariant_9_editing_any_audit_row_makes_verify_fail(db, client, tamper):
    team = Team(db)
    _, alert = ingest(db, make_asset(db), at=T0)
    review(db, alert, team.viewer)
    ok = client.get("/audit/verify", headers=auth(team.admin)).json()
    assert ok["ok"] is True and ok["rows_checked"] > 3

    target = db.scalar(text("SELECT id FROM audit_log WHERE action = 'incident.reviewed' ORDER BY id LIMIT 1"))
    db.execute(text("SET LOCAL session_replication_role = replica"))  # a superuser switching triggers off
    db.execute(text(tamper), {"i": target})
    db.execute(text("SET LOCAL session_replication_role = origin"))
    db.expire_all()
    bad = client.get("/audit/verify", headers=auth(team.viewer)).json()
    assert bad["ok"] is False


# Incident state changes only through the lifecycle --------------------------------------------

def test_state_changes_outside_the_lifecycle_are_refused_by_the_database(db):
    _, alert = ingest(db, make_asset(db), at=T0)
    with pytest.raises(DBAPIError, match="only through the incident lifecycle"):
        with db.begin_nested():
            db.execute(text("UPDATE alerts SET state = 'CLOSED', resolution = 'dismissed', closed_at = now() WHERE id = :i"), {"i": alert.id})


def test_a_new_incident_must_start_open(db):
    asset = make_asset(db)
    out, alert = ingest(db, asset, at=T0)
    with pytest.raises(DBAPIError, match="must start as OPEN"):
        with db.begin_nested():
            cand = Candidate(asset_id=asset.id, boundary_id=bsvc.primary_of(bsvc.current_boundary_set(db, asset.id))["id"],
                             geom=WKTElement("MULTIPOLYGON(((81.5 14.5, 81.501 14.5, 81.501 14.501, 81.5 14.5)))", srid=4326),
                             area_sq_m=5000, change_type="soil_fill", first_changed_at=dt.date(2025, 6, 1), sensor_basis="optical_only",
                             confidence=0.5, rule_version="t", created_at=T0)
            db.add(cand)
            db.flush()
            db.add(Alert(code="X-2", candidate_id=cand.id, state="CONFIRMED", resolution="confirmed", created_at=T0, updated_at=T0))
            db.flush()


def test_resolution_must_match_the_state(db):
    _, alert = ingest(db, make_asset(db), at=T0)
    with pytest.raises(DBAPIError, match="alerts_state_resolution"):
        with db.begin_nested():
            db.execute(text("SELECT set_config('lp.state_machine', 'on', true)"))
            db.execute(text("UPDATE alerts SET state = 'CONFIRMED' WHERE id = :i"), {"i": alert.id})


def test_no_other_module_assigns_incident_state():
    from pathlib import Path

    import re

    root = Path(__file__).resolve().parents[1] / "app"
    assignment = re.compile(r"\.state\s*=(?!=)")
    offenders = []
    for path in root.rglob("*.py"):
        if path.name == "incidents.py":
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if assignment.search(stripped) and "alert" in stripped.lower():
                offenders.append(f"{path.name}:{n}: {stripped}")
    assert offenders == []
