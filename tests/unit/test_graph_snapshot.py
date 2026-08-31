from typing import cast

from sqlalchemy.ext.asyncio import AsyncEngine

from telco_digital.infrastructure.postgres.graph_snapshot import load_graph_snapshot


class _Mappings:
    def __iter__(self):
        return iter(())


class _Result:
    def mappings(self):
        return _Mappings()


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None


class _Connection:
    def __init__(self) -> None:
        self.options: dict[str, str] = {}
        self.execute_count = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def execution_options(self, **options):
        self.options.update(options)
        return self

    def begin(self):
        return _Transaction()

    async def execute(self, _statement):
        self.execute_count += 1
        return _Result()


class _Engine:
    def __init__(self) -> None:
        self.connection = _Connection()
        self.connect_count = 0

    def connect(self):
        self.connect_count += 1
        return self.connection


async def test_graph_snapshot_uses_one_repeatable_read_transaction() -> None:
    engine = _Engine()
    snapshot = await load_graph_snapshot(cast(AsyncEngine, engine))
    assert engine.connect_count == 1
    assert engine.connection.options == {"isolation_level": "REPEATABLE READ"}
    assert engine.connection.execute_count == 15
    assert snapshot.customers == []
