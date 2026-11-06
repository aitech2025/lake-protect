"""Process settings, read from the environment. Secrets have no defaults."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LP_", extra="ignore")

    database_url: str
    test_database_url: str | None = None
    jwt_secret: str
    jwt_ttl_minutes: int = 720
    storage_dir: Path = Path("/var/lp/storage")
    data_dir: Path = Path("/srv/data")
    repo_dir: Path = Path("/srv/repo")
    # Stays False until counsel has reviewed the section 63(4) template. Not settable from the UI.
    counsel_reviewed_template: bool = False


settings = Settings()
