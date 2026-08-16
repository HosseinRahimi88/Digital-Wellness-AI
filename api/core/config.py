"""
api/core/config.py
-------------------
Centralized settings for the FastAPI backend, loaded from environment
variables / a .env file via pydantic-settings. No hardcoded config
values live in routers, middleware, or dependencies - everything reads
from this one Settings object.

This is FastAPI-layer configuration only (host, CORS origins, JWT
expiry, etc.) - it does not duplicate or replace anything under
config/ (e.g. config/recommendation_registry.py), which is business
configuration owned by the services layer.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# The one definition of the project root - see core/paths.py. Computed
# by directory depth here until it wasn't, twice; a path relative to a
# file's own position is correct until something moves and silently
# wrong afterwards, because a Path that does not exist still works.
from core import paths

PROJECT_ROOT = paths.PROJECT_ROOT


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App metadata ---
    app_name: str = "Digital Wellness AI API"
    app_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    debug: bool = False

    # --- CORS ---
    # Comma-separated origins in the env var, e.g.
    # CORS_ALLOWED_ORIGINS=http://localhost:3000,https://app.example.com
    # Empty by default (no cross-origin access) rather than "*" - a
    # production deployment must opt in explicitly.
    cors_allowed_origins: str = ""

    # --- Trusted hosts ---
    # Comma-separated hostnames, e.g. "api.example.com,localhost".
    # "*" (the default) disables the check - set this explicitly in
    # production.
    trusted_hosts: str = "*"

    # --- JWT (delegates actual signing/verification to utils/tokens.py,
    # which already reads JWT_SECRET_KEY itself - this setting only
    # controls API-layer behavior, not the secret itself) ---
    access_token_expire_minutes: int = 60

    # --- Rate/size limits ---
    max_request_body_bytes: int = 2_000_000  # 2 MB - well above any real JSON payload this API accepts

    # --- Pagination ---
    default_page_size: int = 20
    max_page_size: int = 100

    # --- Logging ---
    log_to_file: bool = False
    log_file_path: str = str(PROJECT_ROOT / "logs" / "api.log")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def trusted_hosts_list(self) -> list[str]:
        return [h.strip() for h in self.trusted_hosts.split(",") if h.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton - read once per process, like ModelManager."""
    return Settings()
