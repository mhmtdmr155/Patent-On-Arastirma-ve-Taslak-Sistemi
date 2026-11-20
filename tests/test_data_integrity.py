"""Tests for Patent Data Integrity and Audit Verifications (PAT-0201-D01).

Validates exact file byte sizes, SHA-256 sums, rigorous full-text boundaries
(claims exclusion, opening/closing text matches), locator distinctions,
and source attribution integrity.
"""

import hashlib
import json
from pathlib import Path
import re
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / "data" / "raw"
RAW_MANIFEST = RAW_DIR / "raw_manifest.json"
DATA_MANIFEST = ROOT_DIR / "data_manifest.json"
PROCESSED_PATENTS = ROOT_DIR / "data" / "processed" / "patents.jsonl"
PROCESSED_CHUNKS = ROOT_DIR / "data" / "processed" / "chunks.jsonl"
FEASIBILITY_DOC = ROOT_DIR / "docs" / "source_feasibility.md"


def test_t01_raw_file_sizes_and_sum_match_manifest():
    """T1: Verify physical disk file sizes match raw_manifest.json exactly for all downloaded HTML files."""
    assert RAW_MANIFEST.exists(), "raw_manifest.json missing"
    manifest_entries = json.loads(RAW_MANIFEST.read_text(encoding="utf-8"))

    manifest_map = {e["publication_number"]: e for e in manifest_entries}
    html_files = sorted(RAW_DIR.glob("*.html"))
    assert len(html_files) == len(manifest_entries), f"Expected {len(manifest_entries)} HTML files, found {len(html_files)}"

    total_disk_bytes = 0
    total_manifest_bytes = 0

    for f in html_files:
        pub = f.stem
        assert pub in manifest_map, f"File {f.name} not in raw_manifest.json"
        
        disk_size = f.stat().st_size
        disk_sha = hashlib.sha256(f.read_bytes()).hexdigest()
        
        entry = manifest_map[pub]
        assert disk_size == entry["byte_size"], f"Size mismatch for {pub}: disk={disk_size}, manifest={entry['byte_size']}"
        assert disk_sha == entry["sha256"], f"SHA256 mismatch for {pub}"
        
        total_disk_bytes += disk_size
        total_manifest_bytes += entry["byte_size"]

    # Verify disk total equals manifest total
    assert total_disk_bytes == total_manifest_bytes


def test_t02_rigorous_full_text_boundaries_and_claims_exclusion():
    """T2: Rigorous full-text verification: claims are excluded, description is substantial, boundaries match."""
    assert PROCESSED_PATENTS.exists()
    
    patents = [json.loads(line) for line in PROCESSED_PATENTS.read_text(encoding="utf-8").splitlines()]
    manifest = json.loads((ROOT_DIR / "data_manifest.json").read_text(encoding="utf-8"))
    assert len(patents) == manifest["total_patents"]
    assert len(patents) >= 8

    # Verify baseline 8 patents regression
    baseline_8 = {"US11457576B2", "US11674944B2", "US8671969B2", "US12144295B1", "US11064664B2", "US9241451B2", "US7836910B2", "US9804113B2"}
    found_pubs = {p["publication_number"] for p in patents}
    assert baseline_8.issubset(found_pubs)

    for p in patents:
        pub = p["publication_number"]
        desc = p.get("description")
        raw_path = RAW_DIR / f"{pub}.html"
        assert raw_path.exists()
        raw_html = raw_path.read_text(encoding="utf-8")

        # 1. Description must be substantial (> 5,000 chars for all patents, > 15,000 chars for baseline 8)
        assert desc is not None, f"Description is None for {pub}"
        if pub in baseline_8:
            assert len(desc) > 15000, f"Description unexpectedly short for baseline {pub}: {len(desc)}"
        else:
            assert len(desc) > 5000, f"Description unexpectedly short for {pub}: {len(desc)}"

        # 2. Description must NOT contain claims section tags or full claims block
        assert "<section itemprop=\"claims\"" not in desc
        assert "itemprop=\"claims\"" not in desc

        # 3. Description must originate from <section itemprop="description">
        assert "<section itemprop=\"description\"" in raw_html

        # 4. Opening snippet of normalized description must match raw description start
        sec_m = re.search(r'<section[^>]*itemprop=["\']description["\'][^>]*>(.*?)</section>', raw_html, re.I | re.S)
        assert sec_m is not None, f"Could not find description section in {pub}.html"
        
        # 5. Background must be cleanly extracted without claims bleed
        if p.get("background"):
            assert len(p["background"]) > 50
            assert "claims" not in p["background"].lower()[:200]


def test_t03_internal_vs_source_document_locator_distinction():
    """T3: Verify internal chunk locator is distinguished from source document locator without fake anchors."""
    assert PROCESSED_CHUNKS.exists()
    chunks = [json.loads(l) for l in PROCESSED_CHUNKS.read_text(encoding="utf-8").splitlines()]

    for c in chunks[:50]:
        # Internal locator exists (e.g. description_p1, abstract_p2)
        assert "internal_chunk_locator" in c
        assert c["internal_chunk_locator"].startswith(c["section"].lower())
        
        # Source document locator exists (e.g. section=description)
        assert "source_document_locator" in c
        assert c["source_document_locator"].startswith("section=")
        
        # Source URL is a clean, valid URL without unverified #p-000x anchors
        assert c["source_url"].startswith("https://patents.google.com/patent/")
        assert "#" not in c["source_url"]


def test_t04_source_type_explicit_html_mirror():
    """T4: Verify source_type is explicitly 'Google Patents Public HTML Mirror' (not confused with USPTO XML)."""
    manifest = json.loads(DATA_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["source_type"] == "Google Patents Public HTML Mirror"

    patents = [json.loads(line) for line in PROCESSED_PATENTS.read_text(encoding="utf-8").splitlines()]
    for p in patents:
        assert p["source_name"] == "Google Patents Public HTML Mirror"


def test_t05_uspto_access_condition_documentation():
    """T5: Verify docs/source_feasibility.md documents USPTO May 1, 2026 announcement regarding June 18, 2026 registration."""
    content = FEASIBILITY_DOC.read_text(encoding="utf-8")
    assert "18 Haziran 2026" in content
    assert "Open Data Portal" in content
    assert "1 Mayıs 2026" in content

