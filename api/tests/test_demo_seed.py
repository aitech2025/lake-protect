"""The demo seed: every path from section 13 is present, and every row is fictional and marked."""
import datetime as dt

import pytest
from sqlalchemy import func, select, text

from app.audit import chain
from app.models import Alert, Asset, AuthorisedWork, Candidate, CourtCase, Observation, Permit, User
from app.seed import demo
from app.seed.demo_render import TileRenderer, render_chip
from app.seed.demo_world import World

SEED_DAY = dt.date(2026, 11, 6)


@pytest.fixture()
def seeded(db):
    return demo.Seeder(db, SEED_DAY).run()


def test_every_section_13_path_is_seeded(db, seeded):
    s = seeded["alerts"]
    assert s["headline"] == "TRIAGE"
    assert s["not_real"] == "CLOSED_NOT_REAL"
    assert s["false_alarm"] == "CLOSED_FALSE_ALARM"
    assert s["court_hold"] == "HOLD_LEGAL"
    assert s["watch_list"] == "WATCH_LIST"
    assert s["authorised_work"] == "CLOSED_AUTHORISED"
    assert s["legacy"] == "CLOSED_LEGACY"
    assert s["out_of_scope"] == "CLOSED_OUT_OF_SCOPE"
    assert s["awaiting_boundary"] == "AWAITING_BOUNDARY"
    assert s["full_path"] == "WITH_OFFICER"
    assert s["overdue"] == "ASSIGNED"
    assert s["reopened"] == "TRIAGE"

    by_code = {a.code: a for a in db.scalars(select(Alert))}
    permit_conflict = [a for a in by_code.values() if "permit_conflict" in (db.get(Candidate, a.candidate_id).flags or [])]
    assert len(permit_conflict) == 1 and permit_conflict[0].state == "TRIAGE"
    assert any(a.reopened_count == 1 for a in by_code.values())
    assert seeded["timer_misses"] >= 2  # the overdue assignment and the overdue review


def test_demo_rows_are_all_marked_and_fictional(db, seeded):
    assert all(a.is_demo and a.name.startswith("Demo ") for a in db.scalars(select(Asset)))
    assert all(a.is_demo for a in db.scalars(select(Alert)))
    assert all(o.is_demo and "Not satellite data" in o.licence_notice for o in db.scalars(select(Observation)))
    for model in (Permit, AuthorisedWork, CourtCase):
        assert all(r.is_demo for r in db.scalars(select(model)))
    assert all(u.is_demo and u.name.startswith("Demo ") for u in db.scalars(select(User)))
    assert all(s.startswith("D-") for a in db.scalars(select(Asset)) for s in a.survey_numbers)


def test_demo_geometry_stays_in_open_sea(db, seeded):
    # The demo box sits around 81.5 E, 14.5 N; the nearest coast is about 150 km west of it.
    outside = db.scalar(text("SELECT count(*) FROM candidates WHERE NOT ST_Within(geom, ST_MakeEnvelope(81.4, 14.4, 81.6, 14.6, 4326))"))
    assert outside == 0
    outside_b = db.scalar(text("SELECT count(*) FROM boundaries WHERE NOT ST_Within(geom, ST_MakeEnvelope(81.4, 14.4, 81.6, 14.6, 4326))"))
    assert outside_b == 0


def test_demo_audit_chain_verifies(db, seeded):
    assert chain.verify(db)["ok"] is True


def test_image_chips_are_stored_for_every_alert(db, seeded, isolated_storage):
    for cand in db.scalars(select(Candidate)):
        for key in (cand.before_chip, cand.after_chip):
            head = isolated_storage.head_object(key)
            assert head is not None and head["size"] > 2000


def test_before_and_after_chips_differ_and_are_png(db):
    world = World.load()
    sc = next(s for s in world.spec["scenarios"] if s["key"] == "headline")
    before = render_chip(world, sc, when=dt.date(2026, 10, 18), after=False)
    after = render_chip(world, sc, when=dt.date(2026, 10, 23), after=True)
    assert before.startswith(b"\x89PNG") and after.startswith(b"\x89PNG") and before != after


def test_tile_renderer_draws_a_tile():
    data = TileRenderer(World.load()).render(15, 23801, 15094)
    assert data.startswith(b"\x89PNG")
