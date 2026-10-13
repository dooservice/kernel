from __future__ import annotations

from collections.abc import Sequence

from tortoise import Tortoise

APP_LABEL = "models"


class DatabaseEngine:
    """Owns the Tortoise lifecycle. Schema creation goes through migrations in production;
    `create_schemas` exists only for the test harness."""

    def __init__(self, url: str, model_modules: Sequence[str], migrations: str = "") -> None:
        self.url = url
        self.model_modules = list(model_modules)
        self.migrations = migrations

    def tortoise_config(self) -> dict:
        return {
            "connections": {"default": self.url},
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
