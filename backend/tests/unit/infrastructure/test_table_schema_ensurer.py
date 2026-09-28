import pytest

from src.knowledge_base_backend.infrastructure.database.table_schema_ensurer import TableSchemaEnsurer


class FakeTable:
    def __init__(self, name: str) -> None:
        self.name = name
        self.create_calls = 0

    def create(self, sync_conn, checkfirst: bool = True) -> None:
        self.create_calls += 1


class FakeConnection:
    def __init__(self, table: FakeTable) -> None:
        self._table = table

    async def run_sync(self, fn):
        # Mirrors AsyncConnection.run_sync: invokes the callable with a
        # "sync connection" stand-in and returns its result.
        return fn(object())


class FakeSession:
    def __init__(self, table: FakeTable) -> None:
        self._connection = FakeConnection(table)

    async def connection(self):
        return self._connection


@pytest.mark.asyncio
async def test_ensure_table_exists_creates_table_on_first_call_only() -> None:
    table = FakeTable("learned_keywords")
    session = FakeSession(table)
    ensurer = TableSchemaEnsurer()

    await ensurer.ensure_table_exists(session, table)
    await ensurer.ensure_table_exists(session, table)
    await ensurer.ensure_table_exists(session, table)

    assert table.create_calls == 1


@pytest.mark.asyncio
async def test_ensure_table_exists_swallows_creation_failures() -> None:
    class RaisingTable(FakeTable):
        def create(self, sync_conn, checkfirst: bool = True) -> None:
            raise RuntimeError("permission denied")

    table = RaisingTable("learned_keywords")
    session = FakeSession(table)
    ensurer = TableSchemaEnsurer()

    # Must not raise: a failed auto-creation attempt should never break the
    # caller's main flow.
    await ensurer.ensure_table_exists(session, table)


@pytest.mark.asyncio
async def test_different_tables_are_tracked_independently() -> None:
    table_a = FakeTable("table_a")
    table_b = FakeTable("table_b")
    ensurer = TableSchemaEnsurer()

    await ensurer.ensure_table_exists(FakeSession(table_a), table_a)
    await ensurer.ensure_table_exists(FakeSession(table_b), table_b)

    assert table_a.create_calls == 1
    assert table_b.create_calls == 1
