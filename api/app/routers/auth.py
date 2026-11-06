"""POST /auth/login: demo role accounts only (section 9.5)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import chain
from app.db import get_db
from app.models import User
from app.security import current_user, issue_token

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str


def user_out(user: User) -> dict:
    return {"id": user.id, "username": user.username, "name": user.name, "role": user.role, "language": user.language, "is_demo": user.is_demo}


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.username == body.username))
    if user is None or not user.is_active or not user.is_demo:
        raise HTTPException(401, "Only demo role accounts can log in to the prototype")
    chain.record(db, actor_id=user.id, action="auth.login", entity="user", entity_id=user.id)
    db.commit()
    return {"token": issue_token(user), "user": user_out(user)}


@router.get("/me")
def me(user: User = Depends(current_user)) -> dict:
    return user_out(user)


@router.get("/demo-users")
def demo_users(db: Session = Depends(get_db)) -> list[dict]:
    """The login screen lists the fictional role accounts."""
    users = db.scalars(select(User).where(User.is_demo.is_(True), User.is_active.is_(True)).order_by(User.id))
    return [user_out(u) for u in users]
