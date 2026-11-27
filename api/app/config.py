"""Process settings, read from the environment. Secrets have no defaults."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LP_", extra="ignore")

    database_url: str
    test_database_url: str | None = None
    jwt_secret: str
    jwt_ttl_minutes: int = 720
    # Shared secret the pipeline sends to POST /candidates. Ingest is off when unset.
    pipeline_token: str | None = None
    # Local WhatsApp conversation simulator. Off by default; simulated records are flagged is_demo.
    enable_whatsapp_simulator: bool = False
    storage_dir: Path = Path("/var/lp/storage")
    archive_dir: Path = Path("/var/lp/archive")
    data_dir: Path = Path("/srv/data")
    repo_dir: Path = Path("/srv/repo")
    # Stays False until counsel has reviewed the section 63(4) template. Not settable from the UI.
    counsel_reviewed_template: bool = False

    # Notifications (DECISIONS.md D-059). The desk's address, for links in emails and messages.
    public_url: str = "http://localhost:8180"
    # Email: "file" writes each email to <storage>/outbox/email (the default: nothing leaves the
    # machine); "smtp" sends through the State's mail relay; "off" sends none.
    email_transport: str = "file"
    email_from: str = "GeoGuard <no-reply@geoguard.invalid>"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_starttls: bool = True


settings = Settings()
