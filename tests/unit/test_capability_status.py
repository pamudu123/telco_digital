import re
from pathlib import Path

from telco_digital.application.capability_status import (
    CAPABILITIES,
    STATUS_TABLE_ROWS,
    get_manifest,
)


def test_manifest_keeps_fastapi_and_simulator_not_started() -> None:
    by_number = {item.number: item for item in CAPABILITIES}
    assert by_number["00"].status == "POC complete"
    assert by_number["01"].status == "POC complete"
    assert by_number["02"].status == "POC complete"
    assert by_number["03"].status == "POC complete"
    assert by_number["04"].status == "POC complete"
    assert by_number["05"].status == "POC complete"
    assert by_number["06"].status == "POC complete"
    assert by_number["07"].status == "POC complete"
    assert by_number["12"].status == "Not started"
    assert by_number["12"].name == "FastAPI"
    assert by_number["13"].status == "Not started"
    assert by_number["13"].name == "POC simulator"


def test_features_readme_table_matches_manifest() -> None:
    text = Path("docs/features/README.md").read_text(encoding="utf-8")
    rows = tuple(
        (number, name.strip(), status.strip())
        for number, name, status in re.findall(
            r"^\| (\d{2}) \| ([^|]+) \| ([^|]+) \|", text, flags=re.MULTILINE
        )
    )
    assert rows == STATUS_TABLE_ROWS


def test_manifest_does_not_claim_showcase_completes_later_capabilities() -> None:
    manifest = get_manifest()
    notes = manifest.notes.lower()
    assert "read-only" in notes or "showcase" in notes
    assert all(
        item.status != "POC complete"
        for item in CAPABILITIES
        if item.number not in {"00", "01", "02", "03", "04", "05", "06", "07"}
    )
