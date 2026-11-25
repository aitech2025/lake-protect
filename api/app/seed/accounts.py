"""The role accounts (DECISIONS.md D-065): the sign-in accounts kept when the demo world was removed.

They are listed in `data/accounts.yml`, with the real districts each official covers. Loading is
idempotent: an account that exists is left as it is.
"""
from __future__ import annotations

import datetime as dt

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import OfficialArea, User


def load(db: Session, at: dt.datetime | None = None) -> dict:
    spec = yaml.safe_load((settings.data_dir / "accounts.yml").read_text(encoding="utf-8"))
    at = at or dt.datetime.now(dt.timezone.utc)
    users: dict[str, User] = {}
    made = 0
    for s in spec["users"]:
        user = db.scalar(select(User).where(User.username == s["username"]))
        if user is None:
            user = User(username=s["username"], name=s["name"], role=s["role"], language=s.get("language", "en"), is_demo=True,
                        email=s.get("email"), phone=s.get("phone"), channels=s.get("channels", ["in_app", "email"]))
            db.add(user)
            db.flush()
            made += 1
            admin_id = next((u.id for u in users.values() if u.role == "admin"), None)
            for area in s.get("areas", []):
                db.add(OfficialArea(user_id=user.id, district=area["district"], mandal=area.get("mandal"), added_by=admin_id, added_at=at))
        users[s["username"]] = user
    db.commit()
    return {"accounts": len(users), "created": made}
