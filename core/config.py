from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.errors import AppError


class Settings(BaseSettings):
    app_name: str = "LLM Sample Factory"
    app_env: str = Field(default="development", alias="APP_ENV")
    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    scan_api_key: str = Field(alias="SCAN_API_KEY")
    admin_api_key: str = Field(alias="ADMIN_API_KEY")
    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    import_max_bytes: int = Field(default=1024 * 1024, alias="IMPORT_MAX_BYTES")
    import_max_records: int = Field(default=500, alias="IMPORT_MAX_RECORDS")
    similarity_threshold: float = Field(default=0.55, alias="SIMILARITY_THRESHOLD")
    export_dir: str = Field(default="./data/exports", alias="EXPORT_DIR")
    worker_poll_interval_seconds: float = 1.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    @property
    def testing(self) -> bool:
        return self.app_env == "testing"

    @property
    def export_path(self) -> Path:
        return Path(self.export_dir).resolve()

    def validate_runtime_secrets(self) -> None:
        if self.testing:
            return
        invalid_markers = ("replace-with", "changeme", "placeholder", "example", "test-")
        secret_values = {
            "SCAN_API_KEY": self.scan_api_key,
            "ADMIN_API_KEY": self.admin_api_key,
            "JWT_SECRET_KEY": self.jwt_secret_key,
        }
        for key, value in secret_values.items():
            normalized = value.strip().lower()
            if not normalized or any(marker in normalized for marker in invalid_markers):
                raise AppError(500, f"{key} must be configured with a non-placeholder value.")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_runtime_secrets()
    return settings


def reset_settings() -> None:
    get_settings.cache_clear()
