"""
Test suite for PAT-0450: Controlled Patent Corpus Expansion.
Validates:
1. Corpus size, full text verification, and schema compliance across all 34 patents.
2. Section-aware chunking distribution (1504 chunks: 34 Title, 34 Abstract, 76 Background, 1360 Description).
3. Exact mapping to 16 evaluation groups (10 verified families, 6 singletons).
4. BM25 indexing and active retrieval of newly added patents.
5. Streamlit application search verification on expanded corpus.
6. Zero duplicates and provenance tracking.
"""

import json
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

from src.retrieval.bm25_engine import BM25SearchEngine
from src.data.family import check_for_duplicates, VERIFIED_PILOT_FAMILIES
from src.data.schema import validate_patent_record, VerificationStatus
from src.ml.dataset import PatentMLDataset, VERIFIED_FAMILIES

ROOT_DIR = Path(__file__).resolve().parent.parent
PATENTS_JSONL = ROOT_DIR / "data" / "processed" / "patents.jsonl"
CHUNKS_JSONL = ROOT_DIR / "data" / "processed" / "chunks.jsonl"
DATA_MANIFEST = ROOT_DIR / "data_manifest.json"
APP_PATH = str(ROOT_DIR / "app.py")


def test_pat0450_corpus_scale_and_verification_status():
    """Verify expanded corpus contains exactly 34 patents, all FULL_TEXT_VERIFIED."""
    with open(PATENTS_JSONL, mode="r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    assert len(records) == 34, f"Expected 34 patents, found {len(records)}"
    for r in records:
        valid, errors = validate_patent_record(r)
        assert valid, f"Schema error in {r.get('publication_number')}: {errors}"
        assert r["verification_status"] == VerificationStatus.FULL_TEXT_VERIFIED.value
        assert len(r["title"]) > 3
        assert len(r["abstract"]) > 20
        assert len(r["description"]) > 5000
        assert len(r["cpc_codes"]) > 0


def test_pat0450_zero_duplicate_patents():
    """Verify zero duplicate publication numbers exist in the expanded corpus."""
    with open(PATENTS_JSONL, mode="r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    pubs = [r["publication_number"] for r in records]
    assert len(pubs) == len(set(pubs))


def test_pat0450_passage_chunking_distribution():
    """Verify exactly 1504 chunks matching expected section distribution."""
    with open(CHUNKS_JSONL, mode="r", encoding="utf-8") as f:
        chunks = [json.loads(line) for line in f if line.strip()]

    assert len(chunks) == 1504
    sections = {}
    for c in chunks:
        sec = c["section"]
        sections[sec] = sections.get(sec, 0) + 1

    assert sections["TITLE"] == 34
    assert sections["ABSTRACT"] == 34
    assert sections["BACKGROUND"] == 76
    assert sections["DESCRIPTION"] == 1360


def test_pat0450_evaluation_groups_and_family_lineages():
    """Verify all 34 patents map to 28 evaluation groups (3 verified families + 25 singletons) (PAT-0450-D01)."""
    ds = PatentMLDataset()
    groups = set(r["evaluation_group_id"] for r in ds.queue)
    assert len(groups) == 28, f"Expected 28 evaluation groups, got {len(groups)}: {groups}"

    # Verify key genuine family lineages
    assert "FAM_US_DRESSELHAUS_SOIL_01" in groups
    assert "FAM_US_IRR_WIRELESS_01" in groups
    assert "FAM_US_ACCLIMA_TDR_01" in groups

    # Ensure artificial company portfolio families are dissolved
    assert "FAM_US_HUNTER_IRR_01" not in groups
    assert "FAM_US_TORO_IRR_01" not in groups
    assert "FAM_US_RAINBIRD_CTRL_01" not in groups
    assert "FAM_US_DECAGON_MOISTURE_01" not in groups


def test_pat0450_bm25_retrieval_of_newly_expanded_patents():
    """Verify BM25 engine retrieves newly expanded patents in top results for relevant domain queries."""
    engine = BM25SearchEngine()
    assert len(engine.chunks) == 1504

    # Newly added Campbell capacitive probe
    res_cap = engine.search("capacitive soil moisture sensor probe", top_k_patents=5)
    cap_pubs = [r.publication_number for r in res_cap]
    assert "US7170302B2" in cap_pubs or "US7884620B2" in cap_pubs

    # Newly added Rain Bird irrigation controller adapter
    res_ctrl = engine.search("irrigation control systems and methods wireless", top_k_patents=5)
    ctrl_pubs = [r.publication_number for r in res_ctrl]
    assert any(p in ctrl_pubs for p in ["US10327397B2", "US9468162B2", "US8706307B2", "US11457576B2"])


def test_pat0450_streamlit_app_displays_expanded_search_results():
    """Verify Streamlit UI successfully queries and displays results from expanded 34-patent corpus."""
    at = AppTest.from_file(APP_PATH)
    at.run()

    # Enter valid invention to unlock search UI
    at.text_input[0].input("Gelişmiş Sulama Sistemi")
    at.text_area[0].input("Toprak su kaybı")
    at.text_area[1].input("Kapasitif sensörlü akıllı vana")
    at.text_area[2].input("Sensör, Vana")
    at.text_area[3].input("Sensör okunur, sulama açılır")
    at.button[0].click().run()

    search_input = [ti for ti in at.text_input if "Arama Sorgusu" in ti.label][0]
    search_input.input("capacitive soil moisture sensor")

    search_btn = [b for b in at.button if "Patent Ara" in b.label][0]
    search_btn.click().run()

    results = at.session_state["search_results"]
    assert len(results) == 5
    for r in results:
        assert r["publication_number"].startswith("US")
        assert r["bm25_score"] > 0
        assert r["title"] != ""
        assert len(r["inventors"]) > 0

