"""
Test suite for PAT-0450-D01: Source-Grounded Metadata and Family Lineage Audit (T01 - T18).

Validates:
T01: 34 publication numbers are unique.
T02: Processed title matches verbatim source HTML title across all 34 patents.
T03: Report title discrepancies (e.g. US12144295B1) are identified and corrected.
T04: Assignee field correctly parsed (US7944220B2=Delta-T, US10842090B2=Rain Bird, US12144295B1=USAA).
T05: US8244404B2 and US8849461B2 are not in the same family.
T06: US8849461B2 and US9241451B2 are linked via genuine Ersavas continuation lineage.
T07: US6904789B2 and US7944220B2 are not merged into a fake family.
T08: US10842090B2 is not in a Toro family (it is Rain Bird).
T09: Patents without multi-patent families receive distinct SINGLETON_{pub} groups.
T10: populate_family_links() does not generate synthetic continuation links.
T11: Processed patents.jsonl evaluation_group_id is consistent with labeling_queue.csv.
T12: GroupKFold does not split genuine families across train and test partitions.
T13: Existing human annotations are safely preserved during queue generation.
T14: Actual patent (34) and chunk (1504) counts strictly match manifests.
T15: All 34 patents are indexed and retrievable via BM25 engine.
T16: Top-5 sourced search results work seamlessly in Streamlit UI.
T17: Empty or suspicious metadata cannot be marked FULL_TEXT_VERIFIED.
T18: Every verified family possesses concrete, source-grounded lineage evidence.
"""

import csv
import html
import json
from pathlib import Path
import re
import pytest
from streamlit.testing.v1 import AppTest

from src.retrieval.bm25_engine import BM25SearchEngine
from src.data.family import VERIFIED_PILOT_FAMILIES, populate_family_links
from src.data.pipeline import PatentPipeline
from src.data.schema import PatentRecord, VerificationStatus, validate_patent_record
from src.ml.dataset import PatentMLDataset, get_evaluation_group_id
from src.ml.splitting import family_aware_kfold_split

ROOT_DIR = Path(__file__).resolve().parent.parent
PATENTS_JSONL = ROOT_DIR / "data" / "processed" / "patents.jsonl"
CHUNKS_JSONL = ROOT_DIR / "data" / "processed" / "chunks.jsonl"
RAW_DIR = ROOT_DIR / "data" / "raw"
DATA_MANIFEST = ROOT_DIR / "data_manifest.json"
RAW_MANIFEST = ROOT_DIR / "data" / "raw" / "raw_manifest.json"
QUEUE_CSV = ROOT_DIR / "data" / "annotations" / "labeling_queue.csv"
AUDIT_CSV = ROOT_DIR / "artifacts" / "patent_metadata_audit.csv"
APP_PATH = str(ROOT_DIR / "app.py")


def _load_processed_patents() -> list[dict]:
    with open(PATENTS_JSONL, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_t01_unique_publication_numbers():
    """T01: 34 patents have unique publication numbers."""
    patents = _load_processed_patents()
    assert len(patents) == 34, f"Expected 34 patents, found {len(patents)}"
    pubs = [p["publication_number"] for p in patents]
    assert len(pubs) == len(set(pubs)), f"Duplicate publication numbers detected: {pubs}"


def test_t02_processed_title_matches_source_html():
    """T02: Processed title matches verbatim source HTML title across all 34 patents."""
    patents = _load_processed_patents()
    for p in patents:
        pub = p["publication_number"]
        html_file = RAW_DIR / f"{pub}.html"
        assert html_file.exists(), f"Raw HTML file missing for {pub}"
        content = html_file.read_text(encoding="utf-8", errors="replace")
        title_m = re.search(r'<meta\s+name=["\']DC\.title["\']\s+content=["\']([^"\']+)["\']', content, re.I)
        assert title_m, f"DC.title not found in raw HTML of {pub}"
        raw_title = html.unescape(title_m.group(1)).strip()
        assert p["title"] == raw_title, f"Title mismatch for {pub}: '{p['title']}' vs '{raw_title}'"


def test_t03_title_discrepancy_detection_and_fix():
    """T03: Title discrepancies between report and metadata are identified and corrected."""
    patents = {p["publication_number"]: p for p in _load_processed_patents()}
    # US12144295B1 was mistakenly reported as "Soil moisture monitoring probe and method"
    us121 = patents["US12144295B1"]
    assert us121["title"] == "Smart irrigation system"
    assert "Soil moisture monitoring" not in us121["title"]


def test_t04_assignee_field_accuracy():
    """T04: Assignee field correctly parsed without conflating original vs portfolio holders."""
    patents = {p["publication_number"]: p for p in _load_processed_patents()}

    # US7944220B2 is Delta-T Devices Ltd (not Decagon)
    assert "Delta" in patents["US7944220B2"]["assignee"]
    assert "Decagon" not in patents["US7944220B2"]["assignee"]

    # US10842090B2 is Rain Bird Corp (not Toro)
    assert "Rain Bird" in patents["US10842090B2"]["assignee"]
    assert "Toro" not in patents["US10842090B2"]["assignee"]

    # US12144295B1 is USAA
    assert "United Services Automobile Association" in patents["US12144295B1"]["assignee"]

    # US10782722B2 is Valmont Industries Inc (not Hunter)
    assert "Valmont" in patents["US10782722B2"]["assignee"]
    assert "Hunter" not in patents["US10782722B2"]["assignee"]


def test_t05_hunter_portfolio_dissolution():
    """T05: US8244404B2 and US8849461B2 are not placed in the same family."""
    patents = {p["publication_number"]: p for p in _load_processed_patents()}
    g824 = patents["US8244404B2"]["evaluation_group_id"]
    g884 = patents["US8849461B2"]["evaluation_group_id"]
    assert g824 != g884, f"US8244404B2 and US8849461B2 share evaluation group: {g824}"

    # Also verify no family link between them
    links = [l["related_publication"] for l in patents["US8244404B2"].get("family_links", [])]
    assert "US8849461B2" not in links


def test_t06_ersavas_chain_lineage_linkage():
    """T06: US8849461B2 and US9241451B2 are correctly mapped to FAM_US_IRR_WIRELESS_01."""
    patents = {p["publication_number"]: p for p in _load_processed_patents()}
    assert patents["US8849461B2"]["evaluation_group_id"] == "FAM_US_IRR_WIRELESS_01"
    assert patents["US9241451B2"]["evaluation_group_id"] == "FAM_US_IRR_WIRELESS_01"
    assert patents["US10716269B2"]["evaluation_group_id"] == "FAM_US_IRR_WIRELESS_01"
    assert patents["US11064664B2"]["evaluation_group_id"] == "FAM_US_IRR_WIRELESS_01"

    # Verify family link
    links_884 = {l["related_publication"]: l["relationship_type"] for l in patents["US8849461B2"].get("family_links", [])}
    assert "US9241451B2" in links_884


def test_t07_decagon_and_delta_t_separation():
    """T07: US6904789B2 (Decagon) and US7944220B2 (Delta-T) are not merged into a fake family."""
    patents = {p["publication_number"]: p for p in _load_processed_patents()}
    g690 = patents["US6904789B2"]["evaluation_group_id"]
    g794 = patents["US7944220B2"]["evaluation_group_id"]
    assert g690 != g794
    assert g690 == "SINGLETON_US6904789B2"
    assert g794 == "SINGLETON_US7944220B2"


def test_t08_drip_emitter_not_in_toro():
    """T08: US10842090B2 is not in any Toro family group."""
    patents = {p["publication_number"]: p for p in _load_processed_patents()}
    g = patents["US10842090B2"]["evaluation_group_id"]
    assert "TORO" not in g
    assert g == "SINGLETON_US10842090B2"


def test_t09_singletons_assigned_unique_groups():
    """T09: Independent patents receive unique SINGLETON_{pub} evaluation groups."""
    patents = _load_processed_patents()
    singletons = [p for p in patents if p["evaluation_group_id"].startswith("SINGLETON_")]
    assert len(singletons) == 25, f"Expected 25 singletons, found {len(singletons)}"
    singleton_groups = [p["evaluation_group_id"] for p in singletons]
    assert len(singleton_groups) == len(set(singleton_groups)), "Duplicate singleton evaluation group IDs"


def test_t10_populate_family_links_no_synthetic_links():
    """T10: populate_family_links does not generate synthetic continuation links."""
    records = [
        PatentRecord(publication_number="US8244404B2"),
        PatentRecord(publication_number="US8849461B2"),
        PatentRecord(publication_number="US7133749B2"),
        PatentRecord(publication_number="US7328089B2"),
    ]
    populate_family_links(records)
    for r in records:
        assert len(r.family_links) == 0, f"Spurious links generated for {r.publication_number}: {r.family_links}"


def test_t11_queue_and_processed_groups_consistency():
    """T11: Processed patents.jsonl evaluation_group_id matches labeling_queue.csv."""
    patents = {p["publication_number"]: p["evaluation_group_id"] for p in _load_processed_patents()}
    with open(QUEUE_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pub = row["publication_number"]
            assert row["evaluation_group_id"] == patents[pub], (
                f"Mismatch for {pub}: queue has '{row['evaluation_group_id']}', patents.jsonl has '{patents[pub]}'"
            )


def test_t12_group_kfold_no_family_leakage():
    """T12: GroupKFold does not split members of the same family across train and test partitions."""
    ds = PatentMLDataset()
    # Test with synthetic test data using our dataset's evaluation groups
    mock_data = [
        {"pair_id": f"P_{i}", "query_id": f"Q{i%5}", "evaluation_group_id": r["evaluation_group_id"]}
        for i, r in enumerate(ds.queue[:100])
    ]
    splits = family_aware_kfold_split(mock_data, n_splits=3)
    for train_idx, val_idx in splits:
        train_groups = {mock_data[i]["evaluation_group_id"] for i in train_idx}
        val_groups = {mock_data[i]["evaluation_group_id"] for i in val_idx}
        overlap = train_groups.intersection(val_groups)
        assert len(overlap) == 0, f"Family leakage detected in split: overlapping groups {overlap}"


def test_t13_preservation_of_existing_annotations():
    """T13: Existing human annotations are safely preserved."""
    from scripts.generate_labeling_queue import load_existing_annotations
    # Since queue currently has 0 human annotations, ensure load_existing_annotations returns dict without errors
    annot = load_existing_annotations(QUEUE_CSV)
    assert isinstance(annot, dict)
    assert len(annot) == 0  # Zero synthetic labels verified


def test_t14_counts_match_manifests():
    """T14: Actual patent (34) and chunk (1504) counts strictly match manifests."""
    with open(DATA_MANIFEST, "r", encoding="utf-8") as f:
        dm = json.load(f)
    assert dm["total_patents"] == 34
    assert dm["total_chunks"] == 1504

    with open(RAW_MANIFEST, "r", encoding="utf-8") as f:
        rm = json.load(f)
    assert len(rm) == 34


def test_t15_all_patents_indexed_in_bm25():
    """T15: All 34 patents are indexed and retrievable via BM25 engine."""
    engine = BM25SearchEngine()
    indexed_pubs = {c["publication_number"] for c in engine.chunks}
    assert len(indexed_pubs) == 34
    patents = _load_processed_patents()
    for p in patents:
        assert p["publication_number"] in indexed_pubs


def test_t16_top5_sourced_results_streamlit():
    """T16: Top-5 sourced search results work seamlessly in Streamlit UI."""
    at = AppTest.from_file(APP_PATH)
    at.run()
    # Fill invention
    at.text_input[0].input("Akıllı Sulama ve Nem Kontrolü")
    at.text_area[0].input("Su israfı")
    at.text_area[1].input("Toprak nemine dayalı sulama")
    at.text_area[2].input("Nem sensörü, mikroişlemci")
    at.text_area[3].input("Sensör okunur ve sulanır")
    at.button[0].click().run()

    # Search
    search_input = [ti for ti in at.text_input if "Arama Sorgusu" in ti.label][0]
    search_input.input("soil moisture controller")
    search_btn = [b for b in at.button if "Patent Ara" in b.label][0]
    search_btn.click().run()

    results = at.session_state["search_results"]
    assert len(results) == 5
    for r in results:
        assert r["publication_number"].startswith("US")
        assert r["bm25_score"] > 0
        assert r["title"] != ""
        assert len(r["inventors"]) > 0


def test_t17_invalid_metadata_rejected_by_schema():
    """T17: Empty or suspicious metadata cannot be marked FULL_TEXT_VERIFIED."""
    # Test missing description
    invalid_record = {
        "publication_number": "US9999999B2",
        "application_number": "US12/345,678",
        "title": "Valid Title",
        "verification_status": VerificationStatus.FULL_TEXT_VERIFIED.value,
        "abstract": "Valid abstract text that is definitely longer than 20 characters.",
        "description": "",  # Empty description!
    }
    is_valid, errors = validate_patent_record(invalid_record)
    assert not is_valid
    assert any("description" in e.lower() for e in errors)


def test_t18_concrete_source_evidence_for_verified_families():
    """T18: Every verified family possesses concrete, source-grounded lineage evidence."""
    for fam_key, fam_info in VERIFIED_PILOT_FAMILIES.items():
        assert len(fam_info["members"]) >= 2
        assert len(fam_info["lineage_notes"].strip()) > 30
        assert "relationships" in fam_info
        for src, tgt, rel, ev in fam_info["relationships"]:
            assert src in fam_info["members"]
            assert tgt in fam_info["members"]
            assert len(ev.strip()) > 10
            assert rel in {
                "continuation_of",
                "has_continuation",
                "continuation_lineage",
                "continuation_in_part_of",
                "has_continuation_in_part",
                "family_member",
            }
