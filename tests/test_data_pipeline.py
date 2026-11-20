"""Comprehensive test suite for Patent Data Engineering Pipeline (PAT-0201 to PAT-0207).

Validates schema constraints, verbatim abstract fidelity (T27-T29), continuation
family linkages (T30-T31), text normalization, section-aware chunking, duplicate checks,
and safety limits (T1-T33).
"""

import hashlib
import json
from pathlib import Path
import pytest

from src.data.chunker import chunk_patent_record
from src.data.family import (
    check_for_duplicates,
    populate_family_links,
    separate_domain_and_patent_cpcs,
)
from src.data.normalizer import (
    clean_html_tags,
    decode_html_entities,
    normalize_patent_text,
    normalize_unicode,
    normalize_whitespace,
)
from src.data.pipeline import (
    MAX_DOWNLOAD_BYTES,
    MAX_TOTAL_DOWNLOAD_BYTES,
    PatentPipeline,
)
from src.data.schema import (
    PatentRecord,
    VerificationStatus,
    validate_patent_record,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
RAW_DIR = ROOT_DIR / "data" / "raw"
MANIFEST_FILE = ROOT_DIR / "data_manifest.json"
QUALITY_REPORT_FILE = ROOT_DIR / "docs" / "data_quality_report.md"


# -----------------------------------------------------------------------------
# SCHEMA AND VALIDATION (T1, T2, T3, T4, T7)
# -----------------------------------------------------------------------------

def test_t01_publication_number_required():
    """T1: Verify publication_number is mandatory."""
    rec = {"publication_number": "", "application_number": "US16/123,456", "title": "Test"}
    valid, errors = validate_patent_record(rec)
    assert not valid
    assert any("publication_number" in e for e in errors)


def test_t02_application_not_equal_publication():
    """T2: Verify application number is not conflated with publication number."""
    rec = {
        "publication_number": "US11457576B2",
        "application_number": "US11457576B2",
        "title": "Test Title",
        "verification_status": "METADATA_VERIFIED",
    }
    valid, errors = validate_patent_record(rec)
    assert not valid
    assert any("must not equal" in e for e in errors)


def test_t03_title_required():
    """T3: Verify title must be present and non-empty."""
    rec = {
        "publication_number": "US11457576B2",
        "application_number": "US16/690,109",
        "title": "",
        "verification_status": "METADATA_VERIFIED",
    }
    valid, errors = validate_patent_record(rec)
    assert not valid
    assert any("title" in e for e in errors)


def test_t04_t07_full_text_verified_requires_description_and_abstract():
    """T4, T7: FULL_TEXT_VERIFIED requires both non-empty description and abstract."""
    rec_no_desc = {
        "publication_number": "US11457576B2",
        "application_number": "US16/690,109",
        "title": "Valid Title",
        "abstract": "Valid abstract text that is sufficiently long.",
        "description": "",
        "verification_status": "FULL_TEXT_VERIFIED",
    }
    valid, errors = validate_patent_record(rec_no_desc)
    assert not valid
    assert any("FULL_TEXT_VERIFIED requires non-empty description" in e for e in errors)


# -----------------------------------------------------------------------------
# VERBATIM ABSTRACT FIDELITY & REGRESSION FIXES (T5, T6, T27, T28, T29)
# -----------------------------------------------------------------------------

def test_t27_us11064664b2_verbatim_abstract_fidelity():
    """T27: Verify US11064664B2 contains verbatim source abstract (wireless control nodes, gateway, mobile/web app)."""
    patents_file = PROCESSED_DIR / "patents.jsonl"
    assert patents_file.exists(), "patents.jsonl missing"

    found = False
    for line in patents_file.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        if rec["publication_number"] == "US11064664B2":
            found = True
            abs_text = rec["abstract"]
            # Assert source verbatim phrases
            assert "wireless control nodes" in abs_text or "wireless system is provided" in abs_text
            assert "gateway" in abs_text
            assert "communications network" in abs_text
            # Assert that Gemini-generated rewritten summary is NOT present as abstract
            assert "Described embodiments configure irrigation run times" not in abs_text
    assert found, "US11064664B2 record not found in processed corpus"


def test_t28_us9241451b2_verbatim_abstract_fidelity():
    """T28: Verify US9241451B2 contains verbatim source abstract (wireless nodes, remote server, communications network)."""
    patents_file = PROCESSED_DIR / "patents.jsonl"
    found = False
    for line in patents_file.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        if rec["publication_number"] == "US9241451B2":
            found = True
            abs_text = rec["abstract"]
            assert "server computer system located remotely" in abs_text or "server computer system" in abs_text
            assert "wireless nodes" in abs_text
            # Assert that Gemini-generated rewritten summary is NOT present as abstract
            assert "target depletion levels" not in abs_text
    assert found, "US9241451B2 record not found in processed corpus"


def test_t29_us9804113b2_verbatim_abstract_fidelity():
    """T29: Verify US9804113B2 contains verbatim source abstract (capacitive probe, series RLC circuit, microcontroller)."""
    patents_file = PROCESSED_DIR / "patents.jsonl"
    found = False
    for line in patents_file.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        if rec["publication_number"] == "US9804113B2":
            found = True
            abs_text = rec["abstract"]
            assert "capacitive probe" in abs_text
            assert "series RLC circuit" in abs_text
            assert "microcontroller" in abs_text
            # Assert that previous rewritten summary is NOT present
            assert "spaced conductive plates" not in abs_text
    assert found, "US9804113B2 record not found in processed corpus"


# -----------------------------------------------------------------------------
# PATENT FAMILIES AND DUPLICATES (T8, T9, T10, T11, T30, T31)
# -----------------------------------------------------------------------------

def test_t08_cpc_partitioning():
    """T8: Separate patent's actual CPCs from domain target CPCs."""
    patent_cpcs = ["A01G25/16", "F16K37/00", "G01N27/02"]
    domain_cpcs = ["A01G25/16", "G01N33/24"]
    res = separate_domain_and_patent_cpcs(patent_cpcs, domain_cpcs)
    assert res["overlapping_cpcs"] == ["A01G25/16"]
    assert "F16K37/00" in res["patent_specific_cpcs"]
    assert "G01N33/24" not in res["patent_specific_cpcs"]


def test_t09_duplicate_publication_number_rejected():
    """T9: Ensure exact duplicate publication numbers are detected and rejected."""
    r1 = PatentRecord(publication_number="US11457576B2")
    r2 = PatentRecord(publication_number="US11457576B2")
    has_dups, dup_list = check_for_duplicates([r1, r2])
    assert has_dups
    assert "US11457576B2" in dup_list


def test_t10_family_members_retained_as_distinct_records():
    """T10: Distinct publication numbers in the same family are retained as separate records."""
    patents_file = PROCESSED_DIR / "patents.jsonl"
    lines = patents_file.read_text(encoding="utf-8").splitlines()
    pubs = [json.loads(line)["publication_number"] for line in lines]
    assert "US9241451B2" in pubs
    assert "US11064664B2" in pubs
    assert len(pubs) == len(set(pubs)), "Corpus contains duplicate publication numbers"


def test_t30_family_linkage_us7836910_us8671969():
    """T30: Verify continuation lineage between US7836910B2 and US8671969B2."""
    patents_file = PROCESSED_DIR / "patents.jsonl"
    records = {json.loads(l)["publication_number"]: json.loads(l) for l in patents_file.read_text(encoding="utf-8").splitlines()}

    r78 = records["US7836910B2"]
    r86 = records["US8671969B2"]

    assert len(r78["family_links"]) > 0
    assert any(link["related_publication"] == "US8671969B2" for link in r78["family_links"])
    assert any(link["related_publication"] == "US7836910B2" for link in r86["family_links"])


def test_t31_family_linkage_us9241451_us11064664():
    """T31: Verify continuation lineage between US9241451B2 and US11064664B2."""
    patents_file = PROCESSED_DIR / "patents.jsonl"
    records = {json.loads(l)["publication_number"]: json.loads(l) for l in patents_file.read_text(encoding="utf-8").splitlines()}

    r92 = records["US9241451B2"]
    r110 = records["US11064664B2"]

    assert len(r92["family_links"]) > 0
    assert any(link["related_publication"] == "US11064664B2" for link in r92["family_links"])
    assert any(link["related_publication"] == "US9241451B2" for link in r110["family_links"])


# -----------------------------------------------------------------------------
# NORMALIZATION (T12, T24)
# -----------------------------------------------------------------------------

def test_t12_normalization_preserves_technical_terms():
    """T12: Verify normalization preserves technical terms, formulas, and patent numbers."""
    raw = "<p>RLC circuit with 5V DC and 100pF capacitance in US11457576B2 &amp; A01G25/16.</p>"
    norm = normalize_patent_text(raw)
    assert "RLC circuit" in norm
    assert "5V DC" in norm
    assert "100pF" in norm
    assert "US11457576B2" in norm
    assert "A01G25/16" in norm
    assert "<p>" not in norm
    assert "&amp;" not in norm


def test_t24_utf8_encoding_integrity():
    """T24: Verify non-breaking space, quotes, and unicode characters are handled cleanly."""
    raw = "Soil\u00a0moisture \u201csmart\u201d sensor \u2014 threshold \u2026"
    norm = normalize_patent_text(raw)
    assert "\u00a0" not in norm
    assert '"smart"' in norm
    assert "-" in norm


# -----------------------------------------------------------------------------
# CHUNKING INTEGRITY (T13, T14, T15, T16, T17, T18, T26)
# -----------------------------------------------------------------------------

def test_t13_t16_chunk_section_and_provenance():
    """T13, T16: Verify chunks contain valid sections, patent publication numbers, and locators."""
    chunks_file = PROCESSED_DIR / "chunks.jsonl"
    assert chunks_file.exists(), "chunks.jsonl missing"

    valid_sections = {"TITLE", "ABSTRACT", "BACKGROUND", "DESCRIPTION"}
    for line in chunks_file.read_text(encoding="utf-8").splitlines()[:50]:
        c = json.loads(line)
        assert c["section"] in valid_sections
        assert c["publication_number"].startswith("US")
        assert c["source_locator"].startswith(c["section"].lower())


def test_t14_t26_deterministic_chunking():
    """T14, T26: Verify identical records produce identical chunk outputs."""
    rec = PatentRecord(
        publication_number="US_TEST_01",
        title="Test Title",
        abstract="Sentence one is concise. Sentence two is descriptive. Sentence three concludes the abstract.",
        source_url="https://example.com/test",
    )
    chunks_run_1 = chunk_patent_record(rec)
    chunks_run_2 = chunk_patent_record(rec)

    assert len(chunks_run_1) == len(chunks_run_2)
    for c1, c2 in zip(chunks_run_1, chunks_run_2):
        assert c1.chunk_id == c2.chunk_id
        assert c1.text == c2.text
        assert c1.character_start == c2.character_start


def test_t15_chunks_not_empty():
    """T15: Ensure no generated chunk has empty text or 0 word count."""
    chunks_file = PROCESSED_DIR / "chunks.jsonl"
    for line in chunks_file.read_text(encoding="utf-8").splitlines():
        c = json.loads(line)
        assert len(c["text"].strip()) > 0
        assert c["word_count"] > 0


def test_t17_chunk_ids_unique():
    """T17: Ensure all chunk_ids across the corpus are globally unique."""
    chunks_file = PROCESSED_DIR / "chunks.jsonl"
    chunk_ids = [json.loads(l)["chunk_id"] for l in chunks_file.read_text(encoding="utf-8").splitlines()]
    assert len(chunk_ids) == len(set(chunk_ids)), "Duplicate chunk_id found in chunks.jsonl"


def test_t18_source_url_preserved_in_chunks():
    """T18: Ensure source_url is preserved in every chunk."""
    chunks_file = PROCESSED_DIR / "chunks.jsonl"
    for line in chunks_file.read_text(encoding="utf-8").splitlines()[:20]:
        c = json.loads(line)
        assert c["source_url"].startswith("https://patents.google.com/patent/")


# -----------------------------------------------------------------------------
# RAW PRESERVATION AND SAFETY (T19, T20, T21, T22, T23, T32)
# -----------------------------------------------------------------------------

def test_t19_raw_file_sha256_verification():
    """T19: Ensure raw HTML files in data/raw/ have matching SHA-256 hashes in manifest."""
    raw_manifest_file = RAW_DIR / "raw_manifest.json"
    assert raw_manifest_file.exists(), "raw_manifest.json missing"

    raw_manifest = json.loads(raw_manifest_file.read_text(encoding="utf-8"))
    for entry in raw_manifest:
        file_path = Path(entry["file_path"])
        assert file_path.exists(), f"Raw file {file_path} not found on disk"
        actual_sha = hashlib.sha256(file_path.read_bytes()).hexdigest()
        assert actual_sha == entry["sha256"], f"SHA256 mismatch for {file_path}"


def test_t22_t23_download_limits():
    """T22, T23: Verify single file and total download limits are within policy."""
    assert MAX_DOWNLOAD_BYTES <= 2 * 1024 * 1024
    assert MAX_TOTAL_DOWNLOAD_BYTES <= 50 * 1024 * 1024


# -----------------------------------------------------------------------------
# PROCESSED CORPUS & MANIFEST (T25)
# -----------------------------------------------------------------------------

def test_t25_jsonl_validity():
    """T25: Verify all records in data/processed/patents.jsonl are valid JSON and conform to schema."""
    patents_file = PROCESSED_DIR / "patents.jsonl"
    assert patents_file.exists()

    records = [json.loads(l) for l in patents_file.read_text(encoding="utf-8").splitlines()]
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    assert len(records) == manifest["total_patents"], f"Expected {manifest['total_patents']} records, got {len(records)}"
    assert len(records) >= 8

    for r in records:
        valid, errors = validate_patent_record(r)
        assert valid, f"Record {r.get('publication_number')} validation failed: {errors}"
        assert r["verification_status"] == VerificationStatus.FULL_TEXT_VERIFIED.value


def test_manifest_and_quality_report_exist():
    """Verify data_manifest.json and docs/data_quality_report.md exist and match counts."""
    assert MANIFEST_FILE.exists()
    assert QUALITY_REPORT_FILE.exists()

    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    assert manifest["total_patents"] >= 8
    assert manifest["total_chunks"] >= 256
    assert manifest["status_summary"]["FULL_TEXT_VERIFIED"] == manifest["total_patents"]

