"""Evidence pack (CONTEXT.md section 9.3): a PDF for reading and a zip for integrity.

The zip holds every original and derived file, the PDF, and manifest.json with the SHA-256 of each.
A pack is never overwritten: regenerating adds a version. The section 63(4) certificate stays a
template marked "Draft for counsel review" until counsel_reviewed is set in server configuration.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import io
import json
import zipfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app import __version__ as app_version
from app.audit import chain
from app.clock import as_utc
from app.config import settings
from app.models import (
    Alert,
    Asset,
    AssetDocument,
    Candidate,
    EvidencePack,
    IncidentReview,
    LegalCheck,
    Observation,
    User,
)
from app.rules import config as rules
from app.services import boundaries as bsvc
from app.storage import store

STATEMENT = "Imagery shows physical change. It does not establish title or legality."
TEMPLATES = Path(__file__).with_name("templates")
FONTS = Path(__file__).resolve().parents[1] / "assets" / "fonts"
_env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html"]))

LABELS = {
    "cohort": {"A_RECOVERED": "A, recovered land", "B_FINAL": "B, final notification", "C_PRELIM": "C, preliminary notification",
               "D_UNNOTIFIED": "D, no notification", "E_AGENCY": "E, agency land", "F_REVENUE": "F, revenue land"},
    "status": {"physically_marked": "Marked on the ground", "final_notification": "Final notification",
               "preliminary_notification": "Preliminary notification", "derived": "Estimated outline, not confirmed",
               "surveyed_agency": "Surveyed agency land", "survey_number_only": "Survey number only"},
    "zone": {"inside_ftl": "Inside the lake boundary (FTL) or parcel", "buffer": "In the buffer zone", "watch_ring": "In the 100 m watch ring", "outside": "Outside"},
    "class": {"GOVT_LAND": "Government land", "RESTRICTED_PRIVATE": "Private title claim in a restricted zone", "DISPUTED": "Disputed: court case", "UNKNOWN": "Not yet known"},
    "change": {"soil_fill": "Land fill", "clearing": "Clearing", "levelling": "Levelling", "small_structure": "Construction (small structure)",
               "building": "Construction", "other": "Other change"},
    "stage": {"soil_dumped": "Soil dumped", "land_levelled": "Land levelled", "sheds_fences": "Sheds or fences", "building_rises": "Building rising", "occupied": "Occupied"},
    "sensor": {"optical_and_radar": "Optical and radar", "optical_only": "Optical", "radar_only": "Radar only",
               "citizen_report": "Reported by a citizen, with a satellite review"},
    "review": {"real_change": "A real change", "not_real": "Not a real change", "needs_site_visit": "Needs a site visit"},
}


class PackRefused(Exception):
    pass


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _data_uri(data: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def _iso(v) -> str | None:
    if v is None:
        return None
    if isinstance(v, dt.datetime):
        return v.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return v.isoformat()


def _json(obj) -> bytes:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")


def _render_pdf(html: str) -> bytes:
    from weasyprint import HTML

    return HTML(string=html, base_url=str(TEMPLATES)).write_pdf()


def build(db: Session, alert: Alert, user: User, at: dt.datetime | None = None) -> EvidencePack:
    if alert.resolution != "confirmed":
        raise PackRefused(f"A pack is made for a confirmed change (incident is {alert.state})")
    at = as_utc(at)
    cand = db.get(Candidate, alert.candidate_id)
    asset = db.get(Asset, cand.asset_id)
    primary = bsvc.primary_of(bsvc.boundary_set_at(db, asset.id, at.date()))
    bset = bsvc.boundary_set_at(db, asset.id, at.date())
    lc = db.scalar(select(LegalCheck).where(LegalCheck.candidate_id == cand.id).order_by(LegalCheck.id.desc()).limit(1))
    observations = db.scalars(select(Observation).where(Observation.id.in_(cand.observation_ids or [0])).order_by(Observation.acquired_at)).all()
    users = {u.id: u for u in db.scalars(select(User))}
    reviews = db.scalars(select(IncidentReview).where(IncidentReview.alert_id == alert.id).order_by(IncidentReview.id)).all()
    documents = db.scalars(select(AssetDocument).where(AssetDocument.asset_id == asset.id).order_by(AssetDocument.id)).all()
    version = (db.scalar(select(func.max(EvidencePack.version)).where(EvidencePack.alert_id == alert.id)) or 0) + 1
    counsel_reviewed = bool(settings.counsel_reviewed_template)

    files: dict[str, tuple[bytes, str, str]] = {}  # path -> (bytes, kind, description)
    before = store.get_object(cand.before_chip) if cand.before_chip else b""
    after = store.get_object(cand.after_chip) if cand.after_chip else b""
    if before:
        files["evidence/before.png"] = (before, "derived", f"Last clear image chip, {cand.last_clear_at}, boundary drawn on top")
    if after:
        files["evidence/after.png"] = (after, "derived", f"First changed image chip, {cand.first_changed_at}, same window")
    doc_view = []
    for d in documents:
        if d.file_key:
            data = store.get_object(d.file_key)
            if _sha(data) != d.sha256:
                raise PackRefused(f"Document {d.id} no longer matches the hash recorded when it was added")
            files[f"documents/{d.id}-{d.file_name or 'document'}"] = (data, "original", f"Legal document: {d.title}")
        doc_view.append({"title": d.title, "reference": d.reference, "issued_on": _iso(d.issued_on), "sha256": d.sha256})

    boundary_fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": b["geometry"], "properties": {k: _iso(v) if isinstance(v, (dt.date, dt.datetime)) else v for k, v in b.items() if k != "geometry"}}
        for b in bset.values()
    ]}
    files["evidence/boundary.geojson"] = (_json(boundary_fc), "derived", f"Boundary version {primary['version']} in force on {at.date()}, with its source")
    change_geom = db.scalar(text("SELECT ST_AsGeoJSON(geom)::json FROM candidates WHERE id = :c"), {"c": cand.id})
    files["evidence/change.geojson"] = (_json({"type": "Feature", "geometry": change_geom, "properties": {
        "candidate_id": cand.id, "area_sq_m": float(cand.area_sq_m), "change_type": cand.change_type, "last_clear_at": cand.last_clear_at,
        "first_changed_at": cand.first_changed_at, "sensor_basis": cand.sensor_basis, "rule_version": cand.rule_version}}), "derived", "Outline of the change")
    files["records/legal_check.json"] = (_json({c.name: getattr(lc, c.name) for c in LegalCheck.__table__.columns}), "derived", "Legal check result")
    review_view = [{"reviewer": users[r.reviewer_id].name, "outcome": r.outcome, "outcome_label": LABELS["review"][r.outcome],
                    "note": r.note, "reviewed_at": _iso(r.reviewed_at)} for r in reviews]
    files["records/reviews.json"] = (_json(review_view), "derived", "Reviews recorded by officials")
    history = db.execute(text("SELECT id, actor_id, action, details, at, hash FROM audit_log WHERE entity = 'alert' AND entity_id = :i AND action NOT LIKE 'view.%' ORDER BY id"), {"i": str(alert.id)}).mappings().all()
    decisions = [{"step": h["details"].get("step", h["details"].get("to")), "actor": users[h["actor_id"]].name if h["actor_id"] in users else "System",
                  "at": _iso(h["at"]), "note": h["details"].get("note")}
                 for h in history if h["action"] == "alert.transition"]
    files["records/history.json"] = (_json([dict(h) for h in history]), "derived", "Every logged step on this alert, with its audit hash")
    processing = {
        "software": f"GeoGuard API {app_version}",
        "detection_rules": cand.rule_version,
        "legal_rules": lc.rule_version if lc else None,
        "steps": [
            "Change found by comparing the same window on the last clear and first changed images.",
            "Persistence rule: at least two observations at least 5 days apart, with no reversal.",
            f"Minimum area {rules.rules()['min_candidate_area_sq_m']} sq m.",
            f"Legal check against boundary version {lc.boundary_version if lc else '?'}: zone, baseline date, authorised works, permits, court register, asset mode.",
            "Image chips: true colour, same window for both dates, boundary drawn on top.",
            "Reviews, field visits, the district officer's recommendation and the senior official's approval are taken from the hash-chained audit log.",
            "Legal documents tagged to the asset: each file's hash was recorded when it was added and checked again here.",
        ],
    }
    files["records/processing_note.json"] = (_json(processing), "derived", "Processing note")

    hashed = [{"path": p, "kind": k, "sha256": _sha(b), "bytes": len(b), "description": d} for p, (b, k, d) in sorted(files.items())]
    ctx = {
        "alert": {"code": alert.code, "is_demo": alert.is_demo},
        "asset": {"id": asset.id, "asset_key": asset.asset_key, "name": asset.name, "name_te": asset.name_te, "survey_numbers": asset.survey_numbers,
                  "cohort_label": LABELS["cohort"][asset.cohort]},
        "boundary": {"status_label": LABELS["status"][primary["status"]], "version": primary["version"], "confirmed": rules.is_confirmed_status(primary["status"]),
                     "source_name": primary["source_name"], "source_date": _iso(primary["source_date"]), "source_url": primary["source_url"],
                     "notification_ref": primary["notification_ref"], "valid_from": _iso(primary["valid_from"])},
        "legal": {"zone_label": LABELS["zone"][lc.zone] if lc else "", "class_label": LABELS["class"][lc.alert_class] if lc else ""},
        "candidate": {"last_clear_at": _iso(cand.last_clear_at), "first_changed_at": _iso(cand.first_changed_at), "change_label": LABELS["change"].get(cand.change_type, cand.change_type),
                      "area_sq_m": f"{float(cand.area_sq_m):,.0f}", "area_acres": f"{float(cand.area_sq_m) / 4046.86:.2f}", "sensor_basis": cand.sensor_basis,
                      "sensor_label": LABELS["sensor"][cand.sensor_basis]},
        "observations": [{"sensor": o.sensor, "scene_id": o.scene_id, "acquired_at": _iso(o.acquired_at), "licence_notice": o.licence_notice} for o in observations],
        "resolution": "Sentinel-2, 10 m per pixel",
        "chips": {"before": _data_uri(before, "image/png") if before else "", "after": _data_uri(after, "image/png") if after else ""},
        "processing": processing,
        "hashed_files": hashed,
        "reviews": review_view,
        "decisions": decisions,
        "documents": doc_view,
        "policy_cutoff": rules.policy_cutoff_date().isoformat(),
        "statement": STATEMENT,
        "counsel_reviewed": counsel_reviewed,
        "version": version,
        "generated_at": _iso(at),
        "generated_by": user.name,
        "fonts": {k: (FONTS / f).as_uri() for k, f in {"regular": "NotoSans-Regular.ttf", "bold": "NotoSans-Bold.ttf", "te_regular": "NotoSansTelugu-Regular.ttf", "te_bold": "NotoSansTelugu-Bold.ttf"}.items()},
    }
    certificate = _env.get_template("certificate_page.html").render(**ctx).encode("utf-8")
    pdf = _render_pdf(_env.get_template("case_file.html").render(**ctx))
    files["certificate/section-63-4-template.html"] = (certificate, "derived", "Section 63(4) certificate template" + ("" if counsel_reviewed else ", draft for counsel review"))
    files["case_file.pdf"] = (pdf, "derived", "Case file for reading")

    manifest = {
        "alert_code": alert.code,
        "pack_version": version,
        "generated_at": at.isoformat(),
        "generated_by": user.name,
        "software": processing["software"],
        "is_demo": alert.is_demo,
        "counsel_reviewed": counsel_reviewed,
        "statement": STATEMENT,
        "hash_algorithm": "sha256",
        "files": [{"path": p, "kind": k, "sha256": _sha(b), "bytes": len(b), "description": d} for p, (b, k, d) in sorted(files.items())],
    }
    manifest_bytes = _json(manifest)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        stamp = at.timetuple()[:6]
        for path, (data, _, _) in sorted(files.items()):
            z.writestr(zipfile.ZipInfo(path, date_time=stamp), data)
        z.writestr(zipfile.ZipInfo("manifest.json", date_time=stamp), manifest_bytes)
    base = f"packs/{alert.code}/v{version}"
    pack = EvidencePack(
        alert_id=alert.id, version=version, pdf_path=store.put_object(f"{base}/case_file.pdf", pdf),
        zip_path=store.put_object(f"{base}/{alert.code}-v{version}.zip", buf.getvalue()), manifest_sha256=_sha(manifest_bytes),
        generated_by=user.id, generated_at=at, counsel_reviewed=counsel_reviewed,
    )
    db.add(pack)
    db.flush()
    chain.record(db, actor_id=user.id, action="evidence.generated", entity="alert", entity_id=alert.id,
                 details={"pack_id": pack.id, "version": version, "manifest_sha256": pack.manifest_sha256, "files": len(files), "counsel_reviewed": counsel_reviewed}, at=at)
    return pack
