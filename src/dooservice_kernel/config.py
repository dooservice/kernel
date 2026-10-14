"""The configuration file: the kernel's own sections, and those each module declares.

The kernel reads `[server]`, `[database]`, `[session]`, `[cors]` and `[modules]`. Every
other table belongs to a module, which names it with the `section` of the struct it reads it into
(`BillingConfig.section = "billing"`). A table nobody declares is refused, as an unknown
key inside one is, so a misspelt section stops the process instead of being ignored.
"""

from __future__ import annotations

from collections.abc import Iterable
import os
from pathlib import Path
import tomllib
from typing import Any, TypeVar

import msgspec

from .overrides import EnvironmentOverrides
from .sections import CorsConfig, DatabaseConfig, KernelSections, ModulesConfig, ServerConfig, SessionConfig

DEFAULT_CONFIG_PATH = Path("data/config.toml")
CONFIG_ENV_VAR = "APP_CONFIG"
KERNEL_SECTIONS = frozenset({"server", "database", "session", "cors", "modules"})


S = TypeVar("S")


class UnknownSectionsError(ValueError):
    def __init__(self, names: Iterable[str]) -> None:
        super().__init__(f"no module reads these configuration sections: {', '.join(sorted(names))}")


class Config:
    """The whole file: the kernel's sections as attributes, each module's by its type."""

    def __init__(
        self,
        session: SessionConfig,
        server: ServerConfig | None = None,
        database: DatabaseConfig | None = None,
        cors: CorsConfig | None = None,
        sections: Iterable[Any] = (),
        modules: ModulesConfig | None = None,
    ) -> None:
        self.session = session
        self.server = server or ServerConfig()
        self.database = database or DatabaseConfig()
        self.cors = cors or CorsConfig()
        self.modules = modules or ModulesConfig()
        self.sections: dict[type, Any] = {type(section): section for section in sections}

    def section(self, kind: type[S]) -> S:
        """A module's section, or its defaults when the file has none."""
        found = self.sections.get(kind)
        if found is None:
            found = self.sections[kind] = kind()
        return found

    def put(self, section: Any) -> None:
        """Replace a module's section, as a test or a command that builds its own does."""
        self.sections[type(section)] = section

    @classmethod
    def read(cls, data: dict[str, Any], kinds: Iterable[Any]) -> Config:
        declared = {kind.section: kind for kind in kinds}
        unknown = set(data) - KERNEL_SECTIONS - set(declared)
        if unknown:
            raise UnknownSectionsError(unknown)
        kernel = {name: data[name] for name in KERNEL_SECTIONS if name in data}
        typed = msgspec.convert(kernel, KernelSections, strict=False)
        sections = [msgspec.convert(data[name], kind, strict=False) for name, kind in declared.items() if name in data]
        return cls(typed.session, typed.server, typed.database, typed.cors, sections, typed.modules)

    @classmethod
    def from_toml(cls, path: Path, kinds: Iterable[Any], env_prefix: str = "") -> Config:
        """The file, with whatever the environment overrides under `env_prefix`."""
        with open(path, "rb") as file:
            data = tomllib.load(file)
        return cls.read(EnvironmentOverrides(env_prefix, os.environ).apply(data), kinds)

    @classmethod
    def load(cls, kinds: Iterable[Any], env_var: str = CONFIG_ENV_VAR, env_prefix: str = "") -> Config:
        """The file `env_var` names, or `data/config.toml`, overridden from the environment
        under `env_prefix` when one is given."""
        return cls.from_toml(Path(os.environ.get(env_var, str(DEFAULT_CONFIG_PATH))), kinds, env_prefix)


__all__ = [
    "Config",
    "CorsConfig",
    "DatabaseConfig",
    "ModulesConfig",
    "ServerConfig",
    "SessionConfig",
    "UnknownSectionsError",
]
