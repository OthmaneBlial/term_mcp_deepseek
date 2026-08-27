"""Validated configuration loaded from environment variables."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    log_level: str = "INFO"
    log_file: str = "logs/term_mcp_deepseek.log"
    log_max_bytes: int = 10_485_760
    log_backup_count: int = 5
    session_timeout: int = 3600
    max_concurrent_sessions: int = 10
    secret_key: str = ""
    jwt_secret: str = ""
    max_command_length: int = 1000
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"
    mcp_version: str = "2025-03-26"
    workspace_root: str = "."
    auth_token: str = ""
    allowed_origins: tuple[str, ...] = (
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    )
    approval_mode: str = "inspect"
    allow_network: bool = False
    trust_proxy: bool = False
    command_timeout: float = 20.0
    max_output_bytes: int = 1_048_576
    max_request_bytes: int = 65_536
    rate_limit_per_minute: int = 60
    audit_log: str = ""

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        source = os.environ if environ is None else environ
        return cls(
            host=source.get("HOST", cls.host),
            port=int(source.get("PORT", str(cls.port))),
            debug=_as_bool(source.get("DEBUG", "false")),
            log_level=source.get("LOG_LEVEL", cls.log_level).upper(),
            log_file=source.get("LOG_FILE", cls.log_file),
            log_max_bytes=int(source.get("LOG_MAX_BYTES", str(cls.log_max_bytes))),
            log_backup_count=int(source.get("LOG_BACKUP_COUNT", str(cls.log_backup_count))),
            session_timeout=int(source.get("SESSION_TIMEOUT", str(cls.session_timeout))),
            max_concurrent_sessions=int(
                source.get("MAX_CONCURRENT_SESSIONS", str(cls.max_concurrent_sessions))
            ),
            secret_key=source.get("SECRET_KEY", ""),
            jwt_secret=source.get("JWT_SECRET", ""),
            max_command_length=int(source.get("MAX_COMMAND_LENGTH", str(cls.max_command_length))),
            deepseek_api_key=source.get("DEEPSEEK_API_KEY", ""),
            deepseek_model=source.get("DEEPSEEK_MODEL", cls.deepseek_model),
            deepseek_base_url=source.get("DEEPSEEK_BASE_URL", cls.deepseek_base_url),
            mcp_version=source.get("MCP_VERSION", cls.mcp_version),
            workspace_root=str(Path(source.get("WORKSPACE_ROOT", ".")).resolve()),
            auth_token=source.get("AUTH_TOKEN", ""),
            allowed_origins=tuple(
                origin.strip()
                for origin in source.get(
                    "ALLOWED_ORIGINS",
                    ",".join(cls.allowed_origins),
                ).split(",")
                if origin.strip()
            ),
            approval_mode=source.get("APPROVAL_MODE", cls.approval_mode).lower(),
            allow_network=_as_bool(source.get("ALLOW_NETWORK", "false")),
            trust_proxy=_as_bool(source.get("TRUST_PROXY", "false")),
            command_timeout=float(source.get("COMMAND_TIMEOUT", str(cls.command_timeout))),
            max_output_bytes=int(source.get("MAX_OUTPUT_BYTES", str(cls.max_output_bytes))),
            max_request_bytes=int(source.get("MAX_REQUEST_BYTES", str(cls.max_request_bytes))),
            rate_limit_per_minute=int(
                source.get("RATE_LIMIT_PER_MINUTE", str(cls.rate_limit_per_minute))
            ),
            audit_log=source.get("AUDIT_LOG", ""),
        )

    def as_flask_config(self) -> dict[str, Any]:
        values = {key.upper(): value for key, value in asdict(self).items()}
        values["DEEPSEEK_URL"] = f"{self.deepseek_base_url.rstrip('/')}/chat/completions"
        values["JSON_SORT_KEYS"] = False
        return values

    def validate_for_http(self) -> list[str]:
        errors: list[str] = []
        if len(self.auth_token) < 32:
            errors.append("AUTH_TOKEN must contain at least 32 characters")
        if self.approval_mode not in {"inspect", "confirm", "trusted"}:
            errors.append("APPROVAL_MODE must be inspect, confirm, or trusted")
        workspace = Path(self.workspace_root)
        if not workspace.is_dir():
            errors.append(f"WORKSPACE_ROOT does not exist: {workspace}")
        if not self.allowed_origins:
            errors.append("ALLOWED_ORIGINS must contain at least one origin")
        if "*" in self.allowed_origins:
            errors.append("ALLOWED_ORIGINS cannot contain a wildcard")
        if self.command_timeout <= 0:
            errors.append("COMMAND_TIMEOUT must be greater than zero")
        if self.max_output_bytes < 1024:
            errors.append("MAX_OUTPUT_BYTES must be at least 1024")
        return errors


class Config:
    """Compatibility object backed by the single Settings source."""


def make_legacy_config(settings: Settings | None = None) -> type[Config]:
    selected = settings or Settings.from_env()
    for key, value in selected.as_flask_config().items():
        setattr(Config, key, value)
    return Config


make_legacy_config()
config = Config()
