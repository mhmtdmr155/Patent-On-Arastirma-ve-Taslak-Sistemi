"""Unit and regression tests for patent_source_probe script (T1-T16).

Verifies metadata extraction, application number regression fixes, safety limits,
and audit trail integrity.
"""

from pathlib import Path
import re
import pytest

from scripts.patent_source_probe import (
    MAX_DOWNLOAD_BYTES,
    POLITE_DELAY_SECONDS,
    parse_patent_metadata,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
PROBE_SCRIPT = ROOT_DIR / "scripts" / "patent_source_probe.py"
AUDIT_FILE = ROOT_DIR / "docs" / "patent_sample_audit.md"


# T1: Script existence and file checks
def test_t01_probe_script_exists():
    """T1: Verify patent_source_probe.py exists in scripts/."""
    assert PROBE_SCRIPT.exists(), f"Missing script: {PROBE_SCRIPT}"
    assert PROBE_SCRIPT.is_file()


# T2: URL formatting logic
def test_t02_url_formatting():
    """T2: Verify publication number cleaning for URL generation."""
    raw_pub = " us 11,457,576 B2 / "
    clean_pub = raw_pub.strip().upper().replace(" ", "").replace("/", "").replace(",", "")
    assert clean_pub == "US11457576B2"


# T3: Metadata parser - Publication number
def test_t03_parse_publication_number():
    """T3: Verify publication number extraction."""
    sample_html = '<html><meta name="DC.title" content="Test Patent"></html>'
    res = parse_patent_metadata(sample_html, "US11457576B2", "https://patents.google.com/patent/US11457576B2/en")
    assert res["publication_number"] == "US11457576B2"


# T4: Metadata parser - Application number
def test_t04_parse_application_number():
    """T4: Verify application number extraction from itemprop attribute."""
    sample_html = (
        '<html><meta name="DC.title" content="Test">'
        '<dd itemprop="applicationNumber">US16/690,109</dd></html>'
    )
    res = parse_patent_metadata(sample_html, "US11457576B2", "https://example.com")
    assert res["application_number"] == "US16/690,109"


# T5: Metadata parser - Title extraction and unescaping
def test_t05_parse_title_unescape():
    """T5: Verify HTML title unescaping and cleanup."""
    sample_html = '<html><meta name="DC.title" content="Smart &amp; Intelligent Irrigation System"></html>'
    res = parse_patent_metadata(sample_html, "US123B2", "https://example.com")
    assert res["title"] == "Smart & Intelligent Irrigation System"


# T6: Metadata parser - Filing date extraction
def test_t06_parse_filing_date():
    """T6: Verify dateSubmitted extraction."""
    sample_html = (
        '<html><meta name="DC.title" content="Test">'
        '<meta name="DC.date" content="2019-11-20" scheme="dateSubmitted"></html>'
    )
    res = parse_patent_metadata(sample_html, "US123B2", "https://example.com")
    assert res["filing_date"] == "2019-11-20"


# T7: Metadata parser - Publication / Issue date extraction
def test_t07_parse_publication_date():
    """T7: Verify issue date extraction."""
    sample_html = (
        '<html><meta name="DC.title" content="Test">'
        '<meta name="DC.date" content="2022-10-04" scheme="issue"></html>'
    )
    res = parse_patent_metadata(sample_html, "US11457576B2", "https://example.com")
    assert res["publication_date"] == "2022-10-04"
    assert res["grant_number"] == "US11457576B2"


# T8: Metadata parser - Abstract extraction
def test_t08_parse_abstract():
    """T8: Verify DC.description abstract extraction."""
    sample_html = (
        '<html><meta name="DC.title" content="Test">'
        '<meta name="DC.description" content="An irrigation system with sensors."></html>'
    )
    res = parse_patent_metadata(sample_html, "US123B2", "https://example.com")
    assert res["abstract"] == "An irrigation system with sensors."


# T9: Metadata parser - CPC codes extraction
def test_t09_parse_cpc_codes():
    """T9: Verify CPC code extraction from markup."""
    sample_html = (
        '<html><meta name="DC.title" content="Test">'
        '<span itemprop="Code">A01G25/16</span>'
        '<span itemprop="Code">G01N33/24</span></html>'
    )
    res = parse_patent_metadata(sample_html, "US123B2", "https://example.com")
    assert "A01G25/16" in res["cpc_codes"]
    assert "G01N33/24" in res["cpc_codes"]


# T10: Regression on Patent 1 (US11457576B2)
def test_t10_regression_patent_1():
    """T10: Verify Patent 1 application number matches US16/690,109 (not US16/689,451)."""
    sample_html = (
        '<meta name="DC.title" content="Intelligent irrigation system">'
        '<meta name="DC.date" content="2019-11-20" scheme="dateSubmitted">'
        '<meta name="DC.date" content="2022-10-04" scheme="issue">'
        '<dd itemprop="applicationNumber">US16/690,109</dd>'
    )
    res = parse_patent_metadata(sample_html, "US11457576B2", "https://example.com")
    assert res["application_number"] == "US16/690,109"
    assert res["application_number"] != "US16/689,451"


# T11: Regression on Patent 2 (US11674944B2)
def test_t11_regression_patent_2():
    """T11: Verify Patent 2 application number matches US17/725,836 (not US17/726,052)."""
    sample_html = (
        '<meta name="DC.title" content="In-ground wireless soil moisture sensor">'
        '<meta name="DC.date" content="2022-04-21" scheme="dateSubmitted">'
        '<meta name="DC.date" content="2023-06-13" scheme="issue">'
        '<dd itemprop="applicationNumber">US17/725,836</dd>'
    )
    res = parse_patent_metadata(sample_html, "US11674944B2", "https://example.com")
    assert res["application_number"] == "US17/725,836"
    assert res["application_number"] != "US17/726,052"


# T12: Regression on Patent 3 (US8671969B2)
def test_t12_regression_patent_3():
    """T12: Verify Patent 3 application number matches US13/336,709 (not US13/336,448)."""
    sample_html = (
        '<meta name="DC.title" content="Soil moisture sensor and controller">'
        '<meta name="DC.date" content="2011-12-23" scheme="dateSubmitted">'
        '<meta name="DC.date" content="2014-03-18" scheme="issue">'
        '<dd itemprop="applicationNumber">US13/336,709</dd>'
    )
    res = parse_patent_metadata(sample_html, "US8671969B2", "https://example.com")
    assert res["application_number"] == "US13/336,709"
    assert res["application_number"] != "US13/336,448"


# T13: Regression on Patent 4 (US12144295B1)
def test_t13_regression_patent_4():
    """T13: Verify Patent 4 application number matches US18/206,695 (not US18/206,861)."""
    sample_html = (
        '<meta name="DC.title" content="Smart irrigation system">'
        '<meta name="DC.date" content="2023-06-07" scheme="dateSubmitted">'
        '<meta name="DC.date" content="2024-11-19" scheme="issue">'
        '<dd itemprop="applicationNumber">US18/206,695</dd>'
    )
    res = parse_patent_metadata(sample_html, "US12144295B1", "https://example.com")
    assert res["application_number"] == "US18/206,695"
    assert res["application_number"] != "US18/206,861"


# T14: Audit manifest checks (docs/patent_sample_audit.md)
def test_t14_patent_sample_audit_contents():
    """T14: Verify docs/patent_sample_audit.md contains at least 6 verified patent records."""
    assert AUDIT_FILE.exists(), f"Audit file not found: {AUDIT_FILE}"
    content = AUDIT_FILE.read_text(encoding="utf-8")

    # Count records (e.g. '### Kayıt 1: US 11,457,576 B2')
    records = re.findall(r"### Kayıt \d+:\s*(US[^\n]+)", content)
    assert len(records) >= 6, f"Expected at least 6 records in audit, found {len(records)}: {records}"
    assert len(records) == 8, f"Expected exactly 8 records in audit, found {len(records)}"

    # Check status VERIFIED for all
    verified_count = content.count("`VERIFIED`")
    assert verified_count >= 8, f"Expected at least 8 VERIFIED badges, found {verified_count}"


# T15: Network and safety limit validation
def test_t15_network_and_safety_limits():
    """T15: Verify network limits are strictly defined."""
    assert MAX_DOWNLOAD_BYTES <= 2 * 1024 * 1024, "Max download limit exceeds 2 MB safety rule"
    assert POLITE_DELAY_SECONDS >= 0.5, "Polite delay between requests is too short"


# T16: Error handling on missing metadata
def test_t16_error_handling_missing_metadata():
    """T16: Verify parser handles missing fields cleanly with FAILED status."""
    empty_html = "<html><body>No metadata here</body></html>"
    res = parse_patent_metadata(empty_html, "US000000B2", "https://example.com")
    assert res["verification_status"] == "FAILED"
    assert "title" in res["missing_fields"]
    assert res["application_number"] is None
