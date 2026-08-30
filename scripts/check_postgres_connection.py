"""Verify the configured PostgreSQL connection without exposing credentials."""

from __future__ import annotations

import asyncio

from sqlalchemy.engine import make_url

from telco_digital.config import get_settings
from telco_digital.infrastructure.postgres.session import (
    check_database_connection,
    create_engine,
)


async def main() -> None:
    settings = get_settings()
    url = make_url(settings.database_url)
    engine = create_engine(settings)

    try:
        await check_database_connection(engine)
    finally:
        await engine.dispose()

    print(f"PostgreSQL connection OK: {url.host}:{url.port}/{url.database}")


if __name__ == "__main__":
    asyncio.run(main())
