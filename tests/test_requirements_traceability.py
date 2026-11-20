"""Automated verification test for requirements traceability matrix consistency.

Ensures that docs/requirements_traceability.md maintains exact mathematical
and categorical consistency between its detailed table and summary section.
"""

from pathlib import Path
import re
import pytest

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
TRACEABILITY_FILE = DOCS_DIR / "requirements_traceability.md"


def test_traceability_file_exists():
    """Verify that the requirements traceability file exists."""
    assert TRACEABILITY_FILE.exists(), f"Missing file: {TRACEABILITY_FILE}"
    assert TRACEABILITY_FILE.is_file()


def test_traceability_table_and_summary_consistency():
    """Verify mathematical consistency between table rows and summary section."""
    content = TRACEABILITY_FILE.read_text(encoding="utf-8")

    # Extract table rows (lines starting with '| **' or '| G' or '| K')
    table_lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip().startswith("|")
        and not line.strip().startswith("| Gereksinim Kodu")
        and not line.strip().startswith("| :---")
        and not line.strip().startswith("|---")
    ]

    # Filter out table header / separator lines if any slipped through
    data_rows = [row for row in table_lines if re.search(r"\|\s*(\*\*?[A-Z0-9\.]+\*?\*?)\s*\|", row)]

    assert len(data_rows) == 28, f"Expected 28 requirement rows in table, got {len(data_rows)}"

    # Parse rows: columns are | Code | Category | Desc | File | Test | Evidence | Status | Notes |
    parsed_rows = []
    statuses = {"Uygulandı ve Test Edildi": 0, "Planlandı": 0, "Kısmen Uygulandı": 0, "Engellendi": 0}
    categories = set()

    for row in data_rows:
        cols = [c.strip() for c in row.split("|")[1:-1]]
        assert len(cols) >= 7, f"Row has insufficient columns: {row}"
        req_code = re.sub(r"[\*\_]", "", cols[0]).strip()
        category = cols[1].strip()
        status_raw = cols[6].strip()
        status_clean = re.sub(r"[\*\_]", "", status_raw).strip()

        parsed_rows.append(req_code)
        categories.add(category)

        if "Uygulandı" in status_clean:
            statuses["Uygulandı ve Test Edildi"] += 1
        elif "Planlandı" in status_clean:
            statuses["Planlandı"] += 1
        elif "Kısmen" in status_clean:
            statuses["Kısmen Uygulandı"] += 1
        else:
            statuses["Engellendi"] += 1

    # Check requirement code uniqueness
    assert len(set(parsed_rows)) == 28, f"Duplicate requirement codes detected: {parsed_rows}"

    # Verify counts
    assert statuses["Uygulandı ve Test Edildi"] == 13, f"Expected 13 implemented, got {statuses['Uygulandı ve Test Edildi']}"
    assert statuses["Planlandı"] == 15, f"Expected 15 planned, got {statuses['Planlandı']}"
    assert statuses["Kısmen Uygulandı"] == 0
    assert statuses["Engellendi"] == 0

    # Verify summary section numbers
    summary_total = re.search(r"\* \s*\*\*Toplam Tanımlı Gereksinim:\*\*\s*(\d+)", content)
    summary_impl = re.search(r"\* \s*\*\*Uygulandı ve Test Edildi:\*\*\s*(\d+)", content)
    summary_plan = re.search(r"\* \s*\*\*Planlandı \(Sonraki Aşamalar\):\*\*\s*(\d+)", content)

    assert summary_total is not None, "Summary total requirement count not found"
    assert summary_impl is not None, "Summary implemented count not found"
    assert summary_plan is not None, "Summary planned count not found"

    assert int(summary_total.group(1)) == 28, f"Summary total {summary_total.group(1)} != 28"
    assert int(summary_impl.group(1)) == 13, f"Summary implemented {summary_impl.group(1)} != 13"
    assert int(summary_plan.group(1)) == 15, f"Summary planned {summary_plan.group(1)} != 15"

    # Verify all 7 categories are present
    assert len(categories) == 7, f"Expected 7 categories, found: {categories}"

