from __future__ import annotations

from collections.abc import Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from tortoise import Tortoise

from .constants import APP_LABEL, SQLITE_PRAGMAS


class SqlitePragmas:
    """What every SQLite connection runs with, unless the URL says otherwise.

    WAL with `synchronous=NORMAL` commits without an fsync each time: a power cut can lose
    the last transactions, never corrupt the file, and a commit costs a twentieth. A
    `busy_timeout` makes a writer wait for another instead of failing at once.
    """

    @staticmethod
    def applied(url: str) -> str:
        if not url.startswith("sqlite") or ":memory:" in url:
            return url
        parts = urlsplit(url)
        given = dict(parse_qsl(parts.query))
        return urlunsplit(parts._replace(query=urlencode({**SQLITE_PRAGMAS, **given})))


class DatabaseEngine:
    """Owns the Tortoise lifecycle. Schema creation goes through migrations in production;
    `create_schemas` exists only for the test harness."""

    def __init__(self, url: str, model_modules: Sequence[str], migrations: str = "") -> None:
        self.url = url
        self.model_modules = list(model_modules)
        self.migrations = migrations

    def tortoise_config(self) -> dict:
        return {
            "connections": {"default": SqlitePragmas.applied(self.url)},
            "apps": {
                APP_LABEL: {
                    "models": self.model_modules or [self.__module__],
                    "default_connection": "default",
                    **({"migrations": self.migrations} if self.migrations else {}),
                },
            },
        }

    async def init(self) -> None:
        await Tortoise.init(config=self.tortoise_config(), _enable_global_fallback=True)

    async def create_schemas(self) -> None:
        await Tortoise.generate_schemas(safe=True)

    async def close(self) -> None:
        await Tortoise.close_connections()
