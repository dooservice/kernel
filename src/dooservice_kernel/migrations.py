from __future__ import annotations

import logging

import msgspec
from tortoise import Tortoise, connections
from tortoise.migrations.api.migrate import migrate

from .catalog import TableCatalog
from .constants import APP_LABEL, MIGRATIONS_TABLE
from .db import DatabaseEngine

log = logging.getLogger(__name__)


class Baseline(msgspec.Struct, frozen=True):
    """A database that predates migrations: when `sentinel_table` is there and the
    migrations table is not, `migration` is stamped as applied without running it."""

    migration: str
    sentinel_table: str


class MigrationRunner:
    """Applies native Tortoise migrations. A database the `baseline` describes is
    stamped first, without executing any SQL, so existing data is never touched."""

    def __init__(self, engine: DatabaseEngine, baseline: Baseline | None = None) -> None:
        self.engine = engine
        self.baseline = baseline

    async def table_exists(self, table_name: str) -> bool:
        return await TableCatalog(connections.get("default")).has(table_name)

    async def needs_baseline(self) -> bool:
        if self.baseline is None:
            return False
        await Tortoise.init(config=self.engine.tortoise_config())
        try:
            has_migrations = await self.table_exists(MIGRATIONS_TABLE)
            has_data = await self.table_exists(self.baseline.sentinel_table)
        finally:
            await connections.close_all()
        return not has_migrations and has_data

    async def stamp_baseline(self) -> None:
        assert self.baseline is not None
        log.info("pre-migration database detected: stamping %s without executing SQL", self.baseline.migration)
        await self.run_migrate(target=f"{APP_LABEL}.{self.baseline.migration}", fake=True)

    async def upgrade(self) -> None:
        await self.run_migrate()

    async def run_migrate(self, target: str | None = None, fake: bool = False) -> None:
        await Tortoise.init(config=self.engine.tortoise_config())
        try:
            await migrate(config=self.engine.tortoise_config(), target=target, fake=fake)
        finally:
            await connections.close_all()

    async def ensure_schema(self) -> None:
        if await self.needs_baseline():
            await self.stamp_baseline()
        await self.upgrade()
