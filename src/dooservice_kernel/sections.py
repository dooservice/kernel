"""The kernel's own sections of the configuration file."""

from __future__ import annotations

from typing import Literal

import msgspec


class ServerConfig(msgspec.Struct, forbid_unknown_fields=True):
    host: str = "0.0.0.0"
    port: int = 3000
    public_url: str = "http://localhost:3000"
    frontend_url: str = "http://localhost:5173"
    debug: bool = False
    allow_signups: bool = True
    log_format: Literal["text", "json"] = "text"


class DatabaseConfig(msgspec.Struct, forbid_unknown_fields=True):
    url: str = "sqlite:///data/app.db"


class SessionConfig(msgspec.Struct, forbid_unknown_fields=True):
    secret: str
    ttl_seconds: int = 86400 * 30
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"


class CorsConfig(msgspec.Struct, forbid_unknown_fields=True):
    origins: list[str] = msgspec.field(default_factory=lambda: ["http://localhost:5173"])


class ModulesConfig(msgspec.Struct, forbid_unknown_fields=True):
    """Which modules run: `enabled` names the only ones that do when it is not empty, and
    `disabled` takes some out. Both by `Module.name`."""

    enabled: list[str] = msgspec.field(default_factory=list)
    disabled: list[str] = msgspec.field(default_factory=list)


class KernelSections(msgspec.Struct, forbid_unknown_fields=True):
    session: SessionConfig
    server: ServerConfig = msgspec.field(default_factory=ServerConfig)
    database: DatabaseConfig = msgspec.field(default_factory=DatabaseConfig)
    cors: CorsConfig = msgspec.field(default_factory=CorsConfig)
    modules: ModulesConfig = msgspec.field(default_factory=ModulesConfig)
