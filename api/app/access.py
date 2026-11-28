"""Who may see what (DECISIONS.md D-067). The server is the control; screens only follow it.

- The admin and senior officials see the whole State.
- A district officer sees the assets in their areas (districts, or mandals within a district, set
  on the Officials page), the incidents and citizen reports at those assets, and nothing else.
- A field officer sees the incidents ever assigned to them and the locations of those incidents.

Lists are filtered with `asset_sql` / `alert_sql`; a single record outside a person's scope is
refused with 403 ("outside your area"), so a page can say so instead of looking empty.
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.enums import Role
from app.models import Alert, Asset, Candidate, User
from app.notify.routing import COVERS

STATEWIDE = frozenset({Role.admin.value, Role.senior_official.value})
# The pages and registers that are State-level only.
STATE_READERS = (Role.admin.value, Role.senior_official.value)
# Officers who work incidents (never the admin, D-067).
CASEWORK = (Role.senior_official.value, Role.district_officer.value)

_ASSIGNED = "EXISTS (SELECT 1 FROM incident_assignments ia WHERE ia.alert_id = {alert} AND ia.field_officer_id = {user})"
_ASSIGNED_AT_ASSET = (
    "EXISTS (SELECT 1 FROM incident_assignments ia JOIN alerts x ON x.id = ia.alert_id JOIN candidates xc ON xc.id = x.candidate_id "
    "WHERE xc.asset_id = {asset}.id AND ia.field_officer_id = {user})"
)


def statewide(user: User) -> bool:
    return user.role in STATEWIDE


def asset_sql(user: User, asset_alias: str = "a") -> str:
    """SQL condition on an `assets` alias: the assets this person may see."""
    if statewide(user):
        return "TRUE"
    if user.role == Role.district_officer.value:
        return COVERS.format(user=int(user.id), asset=asset_alias)
    if user.role == Role.field_officer.value:
        return _ASSIGNED_AT_ASSET.format(asset=asset_alias, user=int(user.id))
    return "FALSE"


def alert_sql(user: User, alert_alias: str = "al", asset_alias: str = "a") -> str:
    """SQL condition on an `alerts` alias joined to its asset: the incidents this person may see."""
    if statewide(user):
        return "TRUE"
    if user.role == Role.district_officer.value:
        return COVERS.format(user=int(user.id), asset=asset_alias)
    if user.role == Role.field_officer.value:
        return _ASSIGNED.format(alert=f"{alert_alias}.id", user=int(user.id))
    return "FALSE"


def report_sql(user: User, report_alias: str = "cr") -> str:
    """SQL condition on a `citizen_reports` alias. A report with no place yet is State-level until it is placed."""
    if statewide(user):
        return "TRUE"
    if user.role == Role.district_officer.value:
        return (f"EXISTS (SELECT 1 FROM assets ra WHERE ra.id = {report_alias}.asset_id "
                f"AND {COVERS.format(user=int(user.id), asset='ra')})")
    if user.role == Role.field_officer.value:
        return _ASSIGNED.format(alert=f"{report_alias}.alert_id", user=int(user.id))
    return "FALSE"


def require_report(db: Session, user: User, report_id: int):
    from app.models import CitizenReport

    report = db.get(CitizenReport, report_id)
    if report is None:
        raise HTTPException(404, "Report not found")
    if not statewide(user) and not db.scalar(text(f"SELECT {report_sql(user, 'cr')} FROM citizen_reports cr WHERE cr.id = :i"), {"i": report_id}):
        raise HTTPException(403, OUTSIDE)
    return report


def covers(db: Session, user: User, asset: Asset) -> bool:
    """Is this district officer's area where the asset is?"""
    if user.role != Role.district_officer.value or not (asset.district or "").strip():
        return False
    return bool(db.scalar(text(f"SELECT {COVERS.format(user=int(user.id), asset='a')} FROM assets a WHERE a.id = :a"), {"a": asset.id}))


def can_see_asset(db: Session, user: User, asset: Asset) -> bool:
    if statewide(user):
        return True
    return bool(db.scalar(text(f"SELECT {asset_sql(user, 'a')} FROM assets a WHERE a.id = :a"), {"a": asset.id}))


def can_see_alert(db: Session, user: User, alert: Alert) -> bool:
    if statewide(user):
        return True
    asset_id = db.scalar(text("SELECT asset_id FROM candidates WHERE id = :c"), {"c": alert.candidate_id})
    return bool(db.scalar(text(f"SELECT {alert_sql(user, 'al', 'a')} FROM alerts al, assets a WHERE al.id = :i AND a.id = :a"),
                          {"i": alert.id, "a": asset_id}))


OUTSIDE = "This is outside your area"


def require_asset(db: Session, user: User, asset_id: int) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(404, "Asset not found")
    if not can_see_asset(db, user, asset):
        raise HTTPException(403, OUTSIDE)
    return asset


def require_alert(db: Session, user: User, alert_id: int) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(404, "Incident not found")
    if not can_see_alert(db, user, alert):
        raise HTTPException(403, OUTSIDE)
    return alert


def asset_of(db: Session, alert: Alert) -> Asset:
    return db.get(Asset, db.get(Candidate, alert.candidate_id).asset_id)


def district_officers_for(db: Session, asset: Asset) -> list[User]:
    """The active district officers whose area holds the asset."""
    if not (asset.district or "").strip():
        return []
    ids = db.scalars(text(
        f"SELECT u.id FROM users u, assets a WHERE a.id = :a AND u.is_active AND u.role = 'district_officer' "
        f"AND {COVERS.format(user='u.id', asset='a')} ORDER BY u.id"), {"a": asset.id}).all()
    return [db.get(User, i) for i in ids]


def uncovered(db: Session, asset: Asset) -> bool:
    """No district officer covers the place: the senior official takes the district steps (D-067)."""
    return not district_officers_for(db, asset)
