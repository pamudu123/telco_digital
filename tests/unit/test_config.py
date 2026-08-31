import logging

import pytest
from pydantic import ValidationError

from telco_digital.config import Settings
from telco_digital.config.logging import configure_logging
from telco_digital.infrastructure.postgres.session import async_database_url


def test_provider_postgres_url_uses_asyncpg_driver() -> None:
    url = async_database_url("postgresql://user:password@example.test:5432/database")
    assert url.drivername == "postgresql+asyncpg"


def test_log_level_is_normalized_and_applied() -> None:
    root = logging.getLogger()
    package = logging.getLogger("telco_digital")
    original_root = root.level
    original_package = package.level
    try:
        settings = Settings(log_level="debug")
        configure_logging(settings.log_level)
        assert root.level == logging.DEBUG
        assert package.getEffectiveLevel() == logging.DEBUG
    finally:
        root.setLevel(original_root)
        package.setLevel(original_package)


def test_invalid_log_level_is_rejected() -> None:
    with pytest.raises(ValidationError, match="log_level"):
        Settings(log_level="verbose")
