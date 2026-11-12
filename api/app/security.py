"""Authentication and request-scoped department authorization context."""
from __future__ import annotations
import datetime as dt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.config import settings
from app.db import get_db
from app.models import User

_bearer = HTTPBearer(auto_error=False)
_ALG = "HS256"

def issue_token(user: User) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {"sub": str(user.id), "role": user.role, "iat": now,
               "exp": now + dt.timedelta(minutes=settings.jwt_ttl_minutes)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALG)

def current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
                 db: Session = Depends(get_db)) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Login required")
    try:
        payload = jwt.decode(creds.credentials, settings.jwt_secret, algorithms=[_ALG])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not active")
    # All authorization context is derived from the live database record, never JWT role claims.
    # SET LOCAL semantics ensure the context is cleared at transaction end.
    is_admin = user.role == "admin"
    is_auditor = user.role in {"admin", "auditor"}
    db.execute(text("""
      SELECT set_config('lp.user_id', :user_id, true),
             set_config('lp.is_platform_admin', :is_admin, true),
             set_config('lp.is_auditor', :is_auditor, true),
             set_config('lp.pipeline_ingest', 'false', true)
    """), {
        "user_id": str(user.id),
        "is_admin": "true" if is_admin else "false",
        "is_auditor": "true" if is_auditor else "false",
    })
    return user

def require_roles(*roles: str):
    def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=f"Role {user.role} may not do this")
        return user
    return dependency
