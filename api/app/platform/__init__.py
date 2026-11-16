"""Statewide platform modules.

Import ORM mappings so the canonical tables share the existing declarative
metadata registry. Alembic migrations remain the only DDL authority.
"""
from app.platform import models as models  # noqa: F401
