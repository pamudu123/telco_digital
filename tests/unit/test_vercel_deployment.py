import json
from pathlib import Path

from sqlalchemy.pool import NullPool

from telco_digital.config import Settings
from telco_digital.infrastructure.postgres.session import create_engine

ROOT = Path(__file__).resolve().parents[2]


def test_vercel_entrypoint_exports_the_same_fastapi_app() -> None:
    from app import app as vercel_app

    from telco_digital.api.app import app as package_app

    assert vercel_app is package_app

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'entrypoint = "src.telco_digital.api.app:app"' in pyproject


def test_vercel_bundles_frontend_with_single_fastapi_function() -> None:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))

    assert config["framework"] == "fastapi"
    assert config["fluid"] is True
    assert config["functions"]["app.py"]["includeFiles"] == "frontend/**"
    assert config["functions"]["app.py"]["maxDuration"] == 60
    assert (ROOT / "frontend" / "index.html").is_file()


def test_transaction_pool_mode_disables_application_and_statement_pools() -> None:
    settings = Settings(
        database_url=(
            "postgresql+asyncpg://postgres.project:password@"
            "aws-0-region.pooler.supabase.com:6543/postgres"
        ),
        database_pool_mode="transaction",
    )

    engine = create_engine(settings)
    try:
        assert isinstance(engine.sync_engine.pool, NullPool)
        assert engine.url.query["prepared_statement_cache_size"] == "0"
    finally:
        engine.sync_engine.dispose()


def test_vercel_accepts_a_provider_postgresql_url_without_driver_suffix() -> None:
    settings = Settings(
        database_url=(
            "postgresql://postgres.project:password@"
            "aws-0-region.pooler.supabase.com:6543/postgres"
        ),
        database_pool_mode="transaction",
    )

    engine = create_engine(settings)
    try:
        assert engine.url.drivername == "postgresql+asyncpg"
        assert isinstance(engine.sync_engine.pool, NullPool)
    finally:
        engine.sync_engine.dispose()
