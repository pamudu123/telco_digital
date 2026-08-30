from datetime import datetime


def utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
