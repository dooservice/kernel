"""Migrations run on SQLite and, when `KERNEL_TEST_POSTGRES` names one, on PostgreSQL."""

from __future__ import annotations

from collections.abc import AsyncIterator
import os
from pathlib import Path
import uuid

import asyncpg
import pytest
from tortoise import Tortoise, connections

from dooservice_kernel.db import DatabaseEngine
from dooservice_kernel.migrations import Baseline, MigrationRunner

POSTGRES = os.environ.get("KERNEL_TEST_POSTGRES", "")
BASELINE = Baseline(migration="0001_initial", sentinel_table="notes")


@pytest.fixture(params=["sqlite", "postgres"])
async def url(request: pytest.FixtureRequest, tmp_path: Path) -> AsyncIterator[str]:
    if request.param == "sqlite":
        yield f"sqlite://{tmp_path}/shop.db"
        return
    if not POSTGRES:
        pytest.skip("set KERNEL_TEST_POSTGRES to a server to run against PostgreSQL")
    name = f"kernel_{uuid.uuid4().hex[:8]}"
    admin = await asyncpg.connect(f"{POSTGRES}/postgres")
    await admin.execute(f'CREATE DATABASE "{name}"')
    yield f"{POSTGRES.replace('postgresql://', 'postgres://')}/{name}"
    await admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')
    await admin.close()


def engine(url: str) -> DatabaseEngine:
    return DatabaseEngine(url, ["shop.models"], "shop.migrations")


async def test_a_new_database_gets_every_migration(url: str) -> None:
    await MigrationRunner(engine(url), BASELINE).ensure_schema()

    await Tortoise.init(config=engine(url).tortoise_config())
    try:
        await connections.get("default").execute_query("INSERT INTO notes (id, text, pinned) VALUES (1, 'x', true)")
    finally:
        await connections.close_all()


async def test_a_database_from_before_migrations_is_stamped_and_brought_up(url: str) -> None:
    await Tortoise.init(config=engine(url).tortoise_config())
    try:
        await connections.get("default").execute_script("CREATE TABLE notes (id INT PRIMARY KEY, text VARCHAR(200))")
        await connections.get("default").execute_query("INSERT INTO notes (id, text) VALUES (1, 'kept')")
    finally:
        await connections.close_all()

    await MigrationRunner(engine(url), BASELINE).ensure_schema()

    await Tortoise.init(config=engine(url).tortoise_config())
    try:
        rows = await connections.get("default").execute_query_dict("SELECT text, pinned FROM notes")
    finally:
        await connections.close_all()
    assert [(row["text"], bool(row["pinned"])) for row in rows] == [("kept", False)]
