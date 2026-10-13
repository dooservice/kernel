"""Whether a table exists, asked the way each database Tortoise speaks answers it."""

from __future__ import annotations

from tortoise.backends.base.client import BaseDBAsyncClient

QUESTIONS = {
    "sqlite": "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
    "postgres": (
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = current_schema() AND table_name = $1"
    ),
    "mysql": (
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = DATABASE() AND table_name = %s"
    ),
}


class UnsupportedDatabaseError(RuntimeError):
    def __init__(self, dialect: str) -> None:
        super().__init__(f"the kernel does not know how to list the tables of a {dialect} database")


class TableCatalog:
    def __init__(self, connection: BaseDBAsyncClient) -> None:
        self.connection = connection

    @property
    def question(self) -> str:
        dialect = self.connection.capabilities.dialect
        if dialect not in QUESTIONS:
            raise UnsupportedDatabaseError(dialect)
        return QUESTIONS[dialect]

    async def has(self, table: str) -> bool:
        return bool(await self.connection.execute_query_dict(self.question, [table]))
