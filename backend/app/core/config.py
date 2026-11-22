from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo-root .env, so the API works no matter which directory it is started from.
# In Docker/AWS there is no file; real environment variables are used instead.
ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    """All configuration comes from environment variables (or a local .env file)."""

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str
    redis_url: str
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # Auth. The secret signs JWTs: anyone who has it can forge logins, so it is required
    # (no default) and must be long.
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 7

    # Browser origins allowed to call the API (e.g. Vite dev server).
    cors_origins: list[str] = ["http://localhost:5173"]

    # Rate limits (Redis-backed). Login is limited per (client IP + email) so one attacker
    # can't lock a victim out from elsewhere, plus a looser per-IP cap against email spraying.
    login_max_attempts: int = Field(default=5, ge=1)
    login_ip_max_attempts: int = Field(default=50, ge=1)
    login_window_seconds: int = Field(default=900, ge=1)
    register_max_per_window: int = Field(default=10, ge=1)
    register_window_seconds: int = Field(default=3600, ge=1)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # required fields come from env
