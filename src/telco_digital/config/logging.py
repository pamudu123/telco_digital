from __future__ import annotations

import logging


def configure_logging(level: str) -> None:
    """Apply the configured level without changing host-process logging."""
    normalized = level.upper()
    numeric_level = getattr(logging, normalized, None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Unknown log level: {level}")
    logging.getLogger("telco_digital").setLevel(numeric_level)
