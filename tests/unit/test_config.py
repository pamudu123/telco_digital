import logging
from pathlib import Path

import pytest
from pydantic import ValidationError
from scripts.check_env_variables import documented_env_names, settings_env_names

from telco_digital.config import Settings
from telco_digital.config.logging import configure_logging
from telco_digital.infrastructure.postgres.session import async_database_url


def test_provider_postgres_url_uses_asyncpg_driver() -> None:
    url = async_database_url("postgresql://user:password@example.test:5432/database")
    assert url.drivername == "postgresql+asyncpg"


def test_log_level_is_normalized_and_applied() -> None:
    package = logging.getLogger("telco_digital")
    original_package = package.level
    try:
        settings = Settings(log_level="debug")
        configure_logging(settings.log_level)
        assert package.getEffectiveLevel() == logging.DEBUG
    finally:
        package.setLevel(original_package)


def test_invalid_log_level_is_rejected() -> None:
    with pytest.raises(ValidationError, match="log_level"):
        Settings(log_level="verbose")


def test_env_example_documents_every_settings_field() -> None:
    root = Path(__file__).resolve().parents[2]
    documented = documented_env_names(root / ".env.example")
    required = {name.upper() for name in Settings.model_fields}
    assert required <= documented
    assert required == settings_env_names(root / "src" / "telco_digital" / "config" / "settings.py")
