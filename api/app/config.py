"""Process settings. Secrets have no defaults and must be injected by the runtime."""
from pathlib import Path
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LP_", extra="ignore")
    database_url: str
    test_database_url: str | None = None
    jwt_secret: str
    jwt_ttl_minutes: int = 720
    pipeline_token: str | None = None
    storage_dir: Path = Path("/var/lp/storage")
    storage_backend: Literal["local","s3"] = "local"
    s3_bucket: str | None = None
    s3_endpoint_url: str | None = None
    s3_region: str = "ap-south-1"
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_kms_key_id: str | None = None
    outbox_webhook_url: str | None = None
    outbox_webhook_token: str | None = None
    outbox_batch_size: int = Field(default=25, ge=1, le=200)
    outbox_max_attempts: int = Field(default=12, ge=1, le=50)
    outbox_claim_timeout_seconds: int = Field(default=300, ge=30, le=3600)
    db_pool_size: int = Field(default=10, ge=1, le=100)
    db_max_overflow: int = Field(default=20, ge=0, le=200)
    db_pool_timeout_seconds: int = Field(default=30, ge=1, le=300)
    db_pool_recycle_seconds: int = Field(default=1800, ge=60, le=86400)
    db_statement_timeout_ms: int = Field(default=60000, ge=1000, le=600000)
    data_dir: Path = Path("/srv/data")
    repo_dir: Path = Path("/srv/repo")
    counsel_reviewed_template: bool = False

settings = Settings()
