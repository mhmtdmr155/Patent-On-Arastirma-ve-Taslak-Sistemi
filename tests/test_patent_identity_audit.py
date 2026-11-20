"""
Automated Patent Identity, Metadata, Family Linkage, and Raw File Integrity Audit (PAT-0301-D01).
Tests T01 to T14: Verifies true patent titles, inventors, family continuations,
exact CRLF/LF counts, SHA-256 hashes, and section distributions.
"""

import hashlib
import json
import os
from pathlib import Path
import pytest
from src.data.family import VERIFIED_PILOT_FAMILIES
from src.retrieval.bm25_engine import BM25SearchEngine

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
PATENTS_JSONL = PROCESSED_DIR / "patents.jsonl"
CHUNKS_JSONL = PROCESSED_DIR / "chunks.jsonl"
RAW_MANIFEST = RAW_DIR / "raw_manifest.json"

# Ground Truth Official Titles from Google Patents / USPTO
OFFICIAL_PATENT_METADATA = {
    "US11064664B2": {
        "title": "Methods and systems for irrigation control",
        "app": "US16/933,594",
        "inventors": ["Bulut F. Ersavas", "Semih Pekol", "Atakan Bodur"],
        "assignee": "Rain Bird Corp",
        "raw_size": 962275,
        "crlf_count": 18643,
        "lf_bytes": 943632,
        "sha256": "057294a047526452416aa19d5f5280094f015a66d48b110c57ac71176b365a93",
    },
    "US11457576B2": {
        "title": "Intelligent irrigation system",
        "app": "US16/690,109",
        "inventors": ["Zhongdong HUANG", "Dun ZHENG"],
        "assignee": "Homgar International Inc",
        "raw_size": 205021,
        "crlf_count": 3668,
        "lf_bytes": 201353,
        "sha256": "cfd79eebe8aa4ccf66950203e81b345dae019b8b8ec9e9cd8e05f28eb7a8c2d4",
    },
    "US11674944B2": {
        "title": "In-ground wireless soil moisture sensor",
        "app": "US17/725,836",
        "inventors": ["Rudy Lars Larsen"],
        "assignee": "Smart Rain Systems LLC",
        "raw_size": 280920,
        "crlf_count": 3935,
        "lf_bytes": 276985,
        "sha256": "10074fb850ec18c7fda85675d47215af4bbb6322c4c37d25c60e61f16aeb033b",
    },
    "US12144295B1": {
        "title": "Smart irrigation system",
        "app": "US18/206,695",
        "inventors": ["Gregory David Hansen", "Andre Rene Buentello", "Jose L. Romero, Jr.", "Nina Cooper", "Galo M. Alava"],
        "assignee": "United Services Automobile Association USAA",
        "raw_size": 408179,
        "crlf_count": 5478,
        "lf_bytes": 402701,
        "sha256": "487e57762815f7d6f4e71b5589793641ad199f8e45e5a4cedad973b83699b9d3",
    },
    "US7836910B2": {
        "title": "Soil moisture sensor and controller",
        "app": "US11/097,061",
        "inventors": ["Daniel D. Dresselhaus", "Kevin G. O'Brien"],
        "assignee": "Rain Bird Corp",
        "raw_size": 579063,
        "crlf_count": 8953,
        "lf_bytes": 570110,
        "sha256": "b19c386f6b98d6be653c445a7caab100be2fd02dbb6af1178cecebaf22d0c19d",
    },
    "US8671969B2": {
        "title": "Soil moisture sensor and controller",
        "app": "US13/336,709",
        "inventors": ["Daniel D. Dresselhaus", "Kevin G. O'Brien"],
        "assignee": "Rain Bird Corp",
        "raw_size": 642197,
        "crlf_count": 10530,
        "lf_bytes": 631667,
        "sha256": "aaabd432e42dcb7d250d01116d79aa19d97f90a2396c675726ed71c87708a17c",
    },
    "US9241451B2": {
        "title": "Methods and systems for irrigation control",
        "app": "US14/466,469",
        "inventors": ["Bulut F. Ersavas", "Semih Pekol", "Atakan Bodur"],
        "assignee": "Rain Bird Corp",
        "raw_size": 846832,
        "crlf_count": 15872,
        "lf_bytes": 830960,
        "sha256": "6e75225f5ec1a46f6aa139cb7efe798b85d6aaff533b93f6deab60d87bb18d2e",
    },
    "US9804113B2": {
        "title": "Soil moisture sensor",
        "app": "US14/715,352",
        "inventors": ["Hari Hara Kumaran", "Vibha Tomar"],
        "assignee": "Fiskars Oyj",
        "raw_size": 254660,
        "crlf_count": 4641,
        "lf_bytes": 250019,
        "sha256": "75c0da77e2d47745bd2c848abb7ef8d774f43367d067d51e0b73f4a344396ed8",
    },
}

ERRONEOUS_PARAPHRASED_TITLES = [
    "Soil moisture sensor with integrated temperature sensing",
    "Cloud-based irrigation management system",
    "Soil moisture sensor using resonant frequency measurement",
]


def test_t01_patent_titles_match_official_sources() -> None:
    """T01: All baseline patents in patents.jsonl have official, verified titles."""
    records = {r["publication_number"]: r for r in [json.loads(line) for line in PATENTS_JSONL.read_text(encoding="utf-8").splitlines() if line.strip()]}
    assert len(records) >= 8

    for pub, meta in OFFICIAL_PATENT_METADATA.items():
        assert pub in records, f"Baseline patent {pub} missing from patents.jsonl"
        expected_title = meta["title"]
        assert records[pub]["title"] == expected_title, f"Title mismatch for {pub}: '{records[pub]['title']}' != '{expected_title}'"


def test_t02_search_result_title_equals_patent_record_title() -> None:
    """T02: SearchResult.title strictly equals PatentRecord.title from processed corpus."""
    engine = BM25SearchEngine()
    results = engine.search("soil moisture sensor", top_k_patents=20)
    assert len(results) > 0

    records = {r["publication_number"]: r for r in [json.loads(l) for l in PATENTS_JSONL.read_text(encoding="utf-8").splitlines() if l.strip()]}

    for res in results:
        pub = res.publication_number
        assert pub in records
        assert res.title == records[pub]["title"]
        if pub in OFFICIAL_PATENT_METADATA:
            assert res.title == OFFICIAL_PATENT_METADATA[pub]["title"]


def test_t03_erroneous_titles_not_present_in_corpus_or_results() -> None:
    """T03: The three erroneous paraphrased titles do not exist in corpus or search outputs."""
    corpus_text = PATENTS_JSONL.read_text(encoding="utf-8")
    for bad_title in ERRONEOUS_PARAPHRASED_TITLES:
        assert bad_title not in corpus_text

    engine = BM25SearchEngine()
    for q in ["soil moisture sensor", "wireless irrigation controller", "series RLC circuit"]:
        results = engine.search(q, top_k_patents=20)
        for r in results:
            assert r.title not in ERRONEOUS_PARAPHRASED_TITLES


def test_t04_family_1_correct_inventors_dresselhaus_obrien() -> None:
    """T04: US7836910B2 & US8671969B2 inventors are Dresselhaus & O'Brien (NOT Kates)."""
    records = {r["publication_number"]: r for r in [json.loads(l) for l in PATENTS_JSONL.read_text(encoding="utf-8").splitlines() if l.strip()]}
    
    for pub in ["US7836910B2", "US8671969B2"]:
        rec = records[pub]
        assert "Daniel D. Dresselhaus" in rec["inventors"]
        assert "Kevin G. O'Brien" in rec["inventors"]
        assert "Kates" not in " ".join(rec["inventors"])


def test_t05_family_2_correct_inventors_ersavas_pekol_bodur() -> None:
    """T05: US9241451B2 & US11064664B2 inventors are Ersavas, Pekol, Bodur (NOT Bruhn)."""
    records = {r["publication_number"]: r for r in [json.loads(l) for l in PATENTS_JSONL.read_text(encoding="utf-8").splitlines() if l.strip()]}
    
    for pub in ["US9241451B2", "US11064664B2"]:
        rec = records[pub]
        assert "Bulut F. Ersavas" in rec["inventors"]
        assert "Semih Pekol" in rec["inventors"]
        assert "Atakan Bodur" in rec["inventors"]
        assert "Bruhn" not in " ".join(rec["inventors"])


def test_t06_family_continuation_linkages_verified() -> None:
    """T06: Continuation lineages and family relationships are verified and bidirectional."""
    records = {r["publication_number"]: r for r in [json.loads(l) for l in PATENTS_JSONL.read_text(encoding="utf-8").splitlines() if l.strip()]}
    
    # Family 1
    f1_links_78 = [l["related_publication"] for l in records["US7836910B2"]["family_links"]]
    f1_links_86 = [l["related_publication"] for l in records["US8671969B2"]["family_links"]]
    assert "US8671969B2" in f1_links_78
    assert "US7836910B2" in f1_links_86

    # Family 2
    f2_links_92 = [l["related_publication"] for l in records["US9241451B2"]["family_links"]]
    f2_links_110 = [l["related_publication"] for l in records["US11064664B2"]["family_links"]]
    assert "US11064664B2" in f2_links_92
    assert "US9241451B2" in f2_links_110


def test_t07_no_cross_contamination_of_metadata() -> None:
    """T07: Application numbers, publication numbers, and inventors are strictly partitioned."""
    records = [json.loads(l) for l in PATENTS_JSONL.read_text(encoding="utf-8").splitlines() if l.strip()]
    seen_apps = set()
    seen_pubs = set()

    for r in records:
        pub = r["publication_number"]
        app = r["application_number"]
        assert pub not in seen_pubs
        assert app not in seen_apps
        seen_pubs.add(pub)
        seen_apps.add(app)
        assert app != pub


def test_t08_t11_raw_file_sizes_crlf_and_lf_counts() -> None:
    """T08-T11: Rigorously verifies physical sizes, CRLF counts, and LF sizes of raw files."""
    total_physical = 0
    total_crlf = 0
    total_lf_bytes = 0

    for pub, meta in OFFICIAL_PATENT_METADATA.items():
        file_path = RAW_DIR / f"{pub}.html"
        assert file_path.exists(), f"Raw file missing: {file_path}"

        raw_bytes = file_path.read_bytes()
        file_size = len(raw_bytes)
        crlf_cnt = raw_bytes.count(b"\r\n")
        lf_cnt = raw_bytes.count(b"\n")
        lf_bytes = len(raw_bytes.replace(b"\r\n", b"\n"))

        # Individual file assertions
        assert file_size == meta["raw_size"], f"Physical size mismatch for {pub}: {file_size} != {meta['raw_size']}"
        assert crlf_cnt == meta["crlf_count"], f"CRLF count mismatch for {pub}: {crlf_cnt} != {meta['crlf_count']}"
        assert crlf_cnt == lf_cnt, f"Non-CRLF newlines found in {pub}: {crlf_cnt} != {lf_cnt}"
        assert lf_bytes == meta["lf_bytes"], f"LF bytes mismatch for {pub}: {lf_bytes} != {meta['lf_bytes']}"

        # Exact arithmetic: disk_size - crlf_count == lf_bytes
        assert file_size - crlf_cnt == lf_bytes

        total_physical += file_size
        total_crlf += crlf_cnt
        total_lf_bytes += lf_bytes

    # Aggregate assertions
    assert total_physical == 4179147, f"Total physical size mismatch: {total_physical} != 4179147"
    assert total_crlf == 71720, f"Total CRLF count mismatch: {total_crlf} != 71720"
    assert total_lf_bytes == 4107427, f"Total LF bytes mismatch: {total_lf_bytes} != 4107427"
    assert total_physical - total_crlf == total_lf_bytes


def test_t09_raw_sha256_verification() -> None:
    """T09: Validates SHA-256 hashes of physical files on disk against raw manifest."""
    manifest_entries = {e["publication_number"]: e for e in json.loads(RAW_MANIFEST.read_text(encoding="utf-8"))}

    for pub, meta in OFFICIAL_PATENT_METADATA.items():
        file_path = RAW_DIR / f"{pub}.html"
        actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        assert actual_hash == meta["sha256"]
        assert manifest_entries[pub]["sha256"] == actual_hash


def test_t12_t13_t14_passage_section_distribution() -> None:
    """T12-T14: Verifies the breakdown of sections in chunks.jsonl matching manifest."""
    chunks = [json.loads(line) for line in CHUNKS_JSONL.read_text(encoding="utf-8").splitlines() if line.strip()]
    manifest = json.loads((ROOT_DIR / "data_manifest.json").read_text(encoding="utf-8"))
    assert len(chunks) == manifest["total_chunks"]
    assert len(chunks) >= 256

    section_counts: dict[str, int] = {}
    for c in chunks:
        sec = c["section"]
        section_counts[sec] = section_counts.get(sec, 0) + 1

    # Exact expected section distribution for corpus
    total_patents = manifest["total_patents"]
    assert section_counts["TITLE"] == total_patents, f"Expected {total_patents} TITLE chunks, got {section_counts.get('TITLE')}"
    assert section_counts["ABSTRACT"] == total_patents, f"Expected {total_patents} ABSTRACT chunks, got {section_counts.get('ABSTRACT')}"
    assert section_counts["BACKGROUND"] >= 12, f"Expected >= 12 BACKGROUND chunks, got {section_counts.get('BACKGROUND')}"
    assert section_counts["DESCRIPTION"] >= 228, f"Expected >= 228 DESCRIPTION chunks, got {section_counts.get('DESCRIPTION')}"

    # Verify every patent has exactly 1 TITLE chunk and 1 ABSTRACT chunk
    title_pubs = {c["publication_number"] for c in chunks if c["section"] == "TITLE"}
    abstract_pubs = {c["publication_number"] for c in chunks if c["section"] == "ABSTRACT"}
    assert len(title_pubs) == total_patents
    assert len(abstract_pubs) == total_patents

    # Baseline 8 patents all have Title and Abstract
    baseline_8 = set(OFFICIAL_PATENT_METADATA.keys())
    assert baseline_8.issubset(title_pubs)
    assert baseline_8.issubset(abstract_pubs)

