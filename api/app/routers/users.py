"""GET /users: names and roles for assignment. Nodal officers and admins only."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.enums import Role
from app.models import User
from app.security import require_roles

router = APIRouter(tags=["users"])


@router.get("/users")
def list_users(role: str | None = None, user: User = Depends(require_roles(Role.nodal_officer, Role.admin)), db: Session = Depends(get_db)) -> list[dict]:
    q = select(User).where(User.is_active.is_(True)).order_by(User.name)
    if role:
        q = q.where(User.role == role)
    return [{"id": u.id, "name": u.name, "role": u.role, "is_demo": u.is_demo} for u in db.scalars(q)]
