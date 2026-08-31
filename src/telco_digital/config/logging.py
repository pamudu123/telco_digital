from __future__ import annotations

import logging


def configure_logging(level: str) -> None:
    """Apply the configured level to root and application loggers."""
    normalized = level.upper()
    numeric_level = getattr(logging, normalized, None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Unknown log level: {level}")
    logging.basicConfig(level=numeric_level)
    logging.getLogger().setLevel(numeric_level)
    logging.getLogger("telco_digital").setLevel(numeric_level)
