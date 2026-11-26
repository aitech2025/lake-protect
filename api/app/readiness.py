"""Operational readiness diagnostics.

This endpoint is a configuration checklist, not a production certification. It never
returns secret values, connection strings, filesystem paths or user data.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from sqlalchemy import text


def build_readiness(db: Any, config: Any) -> dict:
    checks: list[dict[str, str]] = []

    try:
        db.execute(text("SELECT 1")).scalar_one()
        migration = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        checks.append({"key": "database", "status": "configured", "detail": "Database connection and migration metadata are reachable"})
        checks.append({"key": "schema_migrations", "status": "configured", "detail": "Migration version is readable"})
    except Exception:
        migration = None
        checks.append({"key": "database", "status": "failed", "detail": "Database or migration metadata is unavailable"})

    storage = Path(config.storage_dir)
    storage_ready = storage.is_dir() and os.access(storage, os.R_OK | os.W_OK | os.X_OK)
    checks.append({
        "key": "object_storage",
        "status": "configured" if storage_ready else "not_configured",
        "detail": "Configured storage directory is accessible" if storage_ready else "Storage directory is missing or not accessible",
    })

    jwt_secret = getattr(config, "jwt_secret", "") or ""
    strong_secret = len(jwt_secret) >= 32
    checks.append({
        "key": "jwt_signing_secret",
        "status": "configured" if strong_secret else "weak_or_missing",
        "detail": "Signing secret meets the minimum length check" if strong_secret else "Use a unique randomly generated secret of at least 32 characters",
    })

    pipeline_ready = bool(getattr(config, "pipeline_token", None))
    checks.append({
        "key": "pipeline_ingestion",
        "status": "configured" if pipeline_ready else "not_configured",
        "detail": "Pipeline authentication token is present" if pipeline_ready else "Pipeline ingestion is disabled until a token is configured",
    })

    public_url = str(getattr(config, "public_url", "") or "")
    public_https = public_url.startswith("https://")
    checks.append({
        "key": "public_url",
        "status": "configured" if public_https else "not_production_url",
        "detail": "Public URL uses HTTPS" if public_https else "Set the externally served HTTPS URL before production",
    })

    transport = str(getattr(config, "email_transport", "off")).lower()
    smtp_ready = bool(getattr(config, "smtp_host", None) and getattr(config, "email_from", None)
                      and not str(getattr(config, "email_from", "")).endswith(".invalid>"))
    email_ready = transport == "smtp" and smtp_ready
    checks.append({
        "key": "email_delivery",
        "status": "configured" if email_ready else "local_or_disabled",
        "detail": "SMTP transport is configured" if email_ready else "Email is local-file or disabled; no external delivery is verified",
    })

    # These gates cannot be certified by environment-variable presence alone.
    for key, detail in (
        ("department_data_isolation", "Department-level database RLS and cross-department isolation require security verification"),
        ("sso_mfa", "Government identity federation and MFA are not verified"),
        ("government_authorization", "Government data-sharing and integration agreements are not recorded as approved"),
        ("high_availability_dr", "High availability, backup restoration and disaster recovery are not verified"),
        ("security_assessment", "Independent security testing and remediation sign-off are not recorded"),
    ):
        checks.append({"key": key, "status": "not_verified", "detail": detail})

    prototype_ready = any(c["key"] == "database" and c["status"] == "configured" for c in checks) and storage_ready
    blockers = [c["key"] for c in checks if c["status"] not in {"configured"}]
    return {
        "overall": "prototype_ready" if prototype_ready else "not_ready",
        "production_ready": False,
        "production_certification": "not_performed",
        "migration_version": migration,
        "checks": checks,
        "production_blockers": blockers,
        "note": "A successful readiness response is not a security audit, government approval or production certification.",
    }
