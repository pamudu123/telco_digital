from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

COUNTRY_ALIASES: dict[str, str] = {
    "LK": "LK",
    "SRI LANKA": "LK",
    "SRILANKA": "LK",
    "SG": "SG",
    "SINGAPORE": "SG",
    "US": "US",
    "USA": "US",
    "UNITED STATES": "US",
    "UNITED STATES OF AMERICA": "US",
    "TH": "TH",
    "THAILAND": "TH",
    "MY": "MY",
    "MALAYSIA": "MY",
    "IN": "IN",
    "INDIA": "IN",
    "GB": "GB",
    "UK": "GB",
    "UNITED KINGDOM": "GB",
}

COUNTRY_DISPLAY: dict[str, str] = {
    "LK": "Sri Lanka",
    "SG": "Singapore",
    "US": "USA",
    "TH": "Thailand",
    "MY": "Malaysia",
    "IN": "India",
    "GB": "United Kingdom",
}


def normalize_country(value: str) -> str:
    key = value.strip().upper()
    if key not in COUNTRY_ALIASES:
        raise ValueError(f"Unsupported country: {value}")
    return COUNTRY_ALIASES[key]


def display_country(code: str) -> str:
    return COUNTRY_DISPLAY.get(code, code)


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "amount", Decimal(self.amount))
        object.__setattr__(self, "currency", self.currency.upper())
