"""
Verification Test Suite for PAT-0404-D02 (Mandatory Tests T01 through T16).
Tests labeling application safety, atomic queue persistence, ML readiness fold feasibility,
and corpus expansion readiness.
"""

import csv
import json
import os
import shutil
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

from src.ml.dataset import PatentMLDataset, get_evaluation_group_id
from src.ml.label_store import LabelStore
from src.ml.readiness import assess_ml_readiness, ReadinessStatus
from src.retrieval.bm25_engine import BM25SearchEngine
from scripts.generate_labeling_queue import (
    load_existing_annotations,
    build_candidate_queue,
    generate_queue,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
PROD_QUEUE_PATH = ROOT_DIR / "data" / "annotations" / "labeling_queue.csv"
CHUNKS_PATH = ROOT_DIR / "data" / "processed" / "chunks.jsonl"
MANIFEST_PATH = ROOT_DIR / "sanitized_manifest.txt"
DATA_MANIFEST_PATH = ROOT_DIR / "data_manifest.json"


# ------------------------------------------------------------------------------
# T01: Henüz etiketlenmemiş kayıt açılınca 0/1/2 seçili değil.
# ------------------------------------------------------------------------------
def test_t01_unannotated_record_opens_with_no_radio_selection(tmp_path):
    """T01: Unannotated record opens in labeling app with radio index=None (no option pre-selected)."""
    app_path = ROOT_DIR / "tools" / "labeling_app.py"
    temp_file = tmp_path / "queue_t01.csv"
    shutil.copy(PROD_QUEUE_PATH, temp_file)

    at = AppTest.from_file(str(app_path), default_timeout=10)
    at.session_state["custom_queue_path"] = temp_file
    at.run()

    radio = next(r for r in at.radio if "İlgililik Seviyesi" in r.label)
    assert radio.value is None, f"Expected unannotated radio.value to be None, got: {radio.value}"


# ------------------------------------------------------------------------------
# T02: Etiket seçmeden Kaydet çalışmaz.
# ------------------------------------------------------------------------------
def test_t02_save_without_selection_is_blocked_and_alerts(tmp_path):
    """T02: Clicking save without selecting an option does NOT persist and triggers error notification."""
    app_path = ROOT_DIR / "tools" / "labeling_app.py"
    temp_file = tmp_path / "queue_t02.csv"
    shutil.copy(PROD_QUEUE_PATH, temp_file)

    at = AppTest.from_file(str(app_path), default_timeout=10)
    at.session_state["custom_queue_path"] = temp_file
    at.run()

    # Click save immediately when value is None
    save_btn = next(b for b in at.button if "Etiketi Kaydet" in b.label)
    save_btn.click().run()

    # Verify notification error exists
    assert any("Lütfen bir ilgililik seviyesi seçiniz" in s.value for s in at.error), "Expected error alert when saving without selection"

    # Verify file was NOT modified
    rows = list(csv.DictReader(open(temp_file, encoding="utf-8")))
    assert rows[0]["human_relevance_label"] == ""
    assert rows[0]["review_status"] == "PENDING_HUMAN_REVIEW"


# ------------------------------------------------------------------------------
# T03: Bilinçli seçilen 0 etiketi kaydedilir.
# ------------------------------------------------------------------------------
def test_t03_conscious_selection_of_label_0_saves_correctly(tmp_path):
    """T03: Explicitly selecting label 0 persists '0' and REVIEWED status to disk."""
    app_path = ROOT_DIR / "tools" / "labeling_app.py"
    temp_file = tmp_path / "queue_t03.csv"
    shutil.copy(PROD_QUEUE_PATH, temp_file)

    at = AppTest.from_file(str(app_path), default_timeout=10)
    at.session_state["custom_queue_path"] = temp_file
    at.run()

    radio = next(r for r in at.radio if "İlgililik Seviyesi" in r.label)
    # Explicitly select Option 0: "0 — İlgisiz / Alan Dışı"
    radio.set_value(radio.options[0]).run()

    save_btn = next(b for b in at.button if "Etiketi Kaydet" in b.label)
    save_btn.click().run()

    rows = list(csv.DictReader(open(temp_file, encoding="utf-8")))
    assert rows[0]["human_relevance_label"] == "0"
    assert rows[0]["review_status"] == "REVIEWED"
    assert rows[0]["reviewer_id"] != ""
    assert rows[0]["reviewed_at"] != ""


# ------------------------------------------------------------------------------
# T04: Var olan 1/2 etiketi geri yüklenir.
# ------------------------------------------------------------------------------
def test_t04_existing_labels_are_preselected_on_revisit(tmp_path):
    """T04: When reopening an already labeled pair (1 or 2), the radio displays that label."""
    app_path = ROOT_DIR / "tools" / "labeling_app.py"
    temp_file = tmp_path / "queue_t04.csv"
    shutil.copy(PROD_QUEUE_PATH, temp_file)

    # Pre-populate Record 0 with label 1 and Record 1 with label 2
    store = LabelStore(queue_path=temp_file)
    records = store.load_records()
    rec0_id = records[0]["pair_id"]
    rec1_id = records[1]["pair_id"]
    store.update_label(rec0_id, label="1", reviewer_id="user_test", notes="Relevant")
    store.update_label(rec1_id, label="2", reviewer_id="user_test", notes="Highly relevant")

    at = AppTest.from_file(str(app_path), default_timeout=10)
    at.session_state["custom_queue_path"] = temp_file
    at.run()

    # Record 0 should have option 1 pre-selected
    radio0 = next(r for r in at.radio if "İlgililik Seviyesi" in r.label)
    assert radio0.value == radio0.options[1]

    # Navigate to Record 1
    next_btn = next(b for b in at.button if "Sonraki" in b.label)
    next_btn.click().run()

    radio1 = next(r for r in at.radio if "İlgililik Seviyesi" in r.label)
    assert radio1.value == radio1.options[2]


# ------------------------------------------------------------------------------
# T05: Gerçek insan etiketi girildikten sonra test paketi başarısızlığa düşmez.
# ------------------------------------------------------------------------------
def test_t05_real_human_labels_in_queue_do_not_break_validation(tmp_path):
    """T05: Queue validation passes when valid human annotations ('0', '1', '2') exist."""
    temp_file = tmp_path / "queue_t05.csv"
    shutil.copy(PROD_QUEUE_PATH, temp_file)

    store = LabelStore(queue_path=temp_file)
    store.update_label("Q01_US11674944B2", label="0", reviewer_id="reviewer_a")
    store.update_label("Q01_US8671969B2", label="1", reviewer_id="reviewer_b")
    store.update_label("Q01_US7836910B2", label="2", reviewer_id="reviewer_a")

    rows = list(csv.DictReader(open(temp_file, encoding="utf-8")))
    for r in rows:
        lbl = r["human_relevance_label"]
        assert lbl in {"", "0", "1", "2"}
        if lbl != "":
            assert r["review_status"] == "REVIEWED"
            assert r["reviewer_id"] in {"reviewer_a", "reviewer_b"}
        else:
            assert r["review_status"] == "PENDING_HUMAN_REVIEW"


# ------------------------------------------------------------------------------
# T06: İzole test fixture'ı gerçek üretim etiketlerini değiştirmez.
# ------------------------------------------------------------------------------
def test_t06_isolated_test_fixtures_never_modify_production_queue(tmp_path):
    """T06: Changes made to a temporary test fixture do not mutate the production queue file."""
    temp_file = tmp_path / "isolated_queue.csv"
    shutil.copy(PROD_QUEUE_PATH, temp_file)

    # Get production queue mtime and hash before mutation
    prod_mtime_before = PROD_QUEUE_PATH.stat().st_mtime
    with open(PROD_QUEUE_PATH, "rb") as f:
        prod_bytes_before = f.read()

    store = LabelStore(queue_path=temp_file)
    store.update_label("Q01_US11674944B2", label="2", reviewer_id="isolated_user")

    prod_mtime_after = PROD_QUEUE_PATH.stat().st_mtime
    with open(PROD_QUEUE_PATH, "rb") as f:
        prod_bytes_after = f.read()

    assert prod_bytes_before == prod_bytes_after, "Production queue was modified by isolated test!"
    assert prod_mtime_before == prod_mtime_after


# ------------------------------------------------------------------------------
# T07: Bozuk CSV okuma sırasında kuyruk yeniden oluşturulup veri kaybı yaşanmaz.
# ------------------------------------------------------------------------------
def test_t07_corrupted_csv_read_aborts_regeneration_without_overwriting(tmp_path):
    """T07: load_existing_annotations strictly raises RuntimeError on corrupted or invalid CSV."""
    corrupt_file = tmp_path / "corrupt_queue.csv"
    with open(corrupt_file, "w", encoding="utf-8") as f:
        f.write("invalid,header,without,pair_id\n1,2,3,4\n")

    with pytest.raises(RuntimeError, match="missing required columns"):
        load_existing_annotations(corrupt_file)

    # Original corrupt file must still be intact on disk
    with open(corrupt_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert "invalid,header,without,pair_id" in content


# ------------------------------------------------------------------------------
# T08: Mevcut insan etiketleri rejenerasyon sonrasında korunur.
# ------------------------------------------------------------------------------
def test_t08_existing_human_labels_preserved_after_queue_regeneration(tmp_path):
    """T08: Regenerating queue preserves all existing human annotations and reviewer metadata."""
    temp_file = tmp_path / "queue_t08.csv"
    shutil.copy(PROD_QUEUE_PATH, temp_file)

    store = LabelStore(queue_path=temp_file)
    store.update_label("Q01_US11674944B2", label="2", reviewer_id="annotator_ksu", notes="Key reference")
    store.update_label("Q01_US8671969B2", label="0", reviewer_id="annotator_ksu", notes="Out of scope")

    # Run queue regeneration targeting temp_file
    generate_queue(queue_path=temp_file)

    rows = list(csv.DictReader(open(temp_file, encoding="utf-8")))
    assert len(rows) >= 160

    rec1 = next(r for r in rows if r["pair_id"] == "Q01_US11674944B2")
    assert rec1["human_relevance_label"] == "2"
    assert rec1["review_status"] == "REVIEWED"
    assert rec1["reviewer_id"] == "annotator_ksu"
    assert rec1["review_notes"] == "Key reference"

    rec2 = next(r for r in rows if r["pair_id"] == "Q01_US8671969B2")
    assert rec2["human_relevance_label"] == "0"
    assert rec2["review_status"] == "REVIEWED"
    assert rec2["reviewer_id"] == "annotator_ksu"


# ------------------------------------------------------------------------------
# T09: Yeni patent eklenince eski etiketler korunur ve yeni çiftler oluşturulur.
# ------------------------------------------------------------------------------
def test_t09_corpus_expansion_retains_old_labels_and_adds_new_pairs():
    """T09: Adding a new patent to corpus retains existing annotations and appends new candidate pairs."""
    ds = PatentMLDataset()
    q_first = list(ds.queries.values())[0]
    existing_labels = {
        "Q01_US11674944B2": {
            "human_relevance_label": "2",
            "reviewer_id": "user_a",
            "review_status": "REVIEWED",
            "review_notes": "Important note",
            "reviewed_at": "2026-11-05T10:00:00",
            "query_text": q_first["query_text"],
        }
    }

    # Add a mock patent
    expanded_patents = list(ds.patents.values()) + [{
        "publication_number": "US9999999B2",
        "title": "Expanded Novel Irrigation Sensor",
        "abstract": "A novel soil moisture sensor apparatus.",
        "description": "Novel detailed sensor description.",
        "cpc_codes": ["A01G25/16"],
        "ipc_codes": ["A01G25/00"],
        "family_id": "FAM_NEW_EXPANSION_01",
        "inventors": ["Test Inventor"],
        "assignee": "Test Assignee",
        "publication_date": "2024-01-01",
    }]

    new_queue = build_candidate_queue(
        queries=list(ds.queries.values()),
        patents=expanded_patents,
        chunks=list(ds.chunks.values()),
        existing_labels=existing_labels,
    )

    # 20 queries * N patents = expected count
    expected_pairs = len(ds.queries) * len(expanded_patents)
    assert len(new_queue) == expected_pairs

    # Old label preserved
    annotated = next(r for r in new_queue if r["pair_id"] == "Q01_US11674944B2")
    assert annotated["human_relevance_label"] == "2"
    assert annotated["review_status"] == "REVIEWED"
    assert annotated["reviewer_id"] == "user_a"

    # New patent pairs are pending
    new_pairs = [r for r in new_queue if r["publication_number"] == "US9999999B2"]
    assert len(new_pairs) == 20
    for p in new_pairs:
        assert p["human_relevance_label"] == ""
        assert p["review_status"] == "PENDING_HUMAN_REVIEW"
        assert p["family_id"] == "FAM_NEW_EXPANSION_01"


# ------------------------------------------------------------------------------
# T10: 50 etiket fakat sadece 2 aile grubu varsa planlanan 3 fold için READY verilmez.
# ------------------------------------------------------------------------------
def test_t10_readiness_blocks_ready_when_only_two_evaluation_groups_labeled():
    """T10: assess_ml_readiness returns PARTIAL (NOT READY) when 50 labels span only 2 evaluation groups."""
    ds = PatentMLDataset()
    mock_ds = PatentMLDataset.__new__(PatentMLDataset)

    # Create 50 labeled pairs across only 2 groups (e.g., FAM_US_DRESSELHAUS_SOIL_01 and FAM_US_IRR_WIRELESS_01)
    two_groups = {"FAM_US_DRESSELHAUS_SOIL_01", "FAM_US_IRR_WIRELESS_01"}
    mock_queue = [dict(r) for r in ds.queue]

    count = 0
    for row in mock_queue:
        if row["evaluation_group_id"] in two_groups and count < 50:
            row["human_relevance_label"] = "1" if count % 2 == 0 else "0"
            row["review_status"] = "REVIEWED"
            row["reviewer_id"] = "reviewer_ksu"
            row["reviewed_at"] = "2026-11-05T12:00:00"
            count += 1

    mock_ds.queue = mock_queue
    readiness = assess_ml_readiness(mock_ds, min_labels_required=50, n_splits=3)

    assert readiness["status"] == ReadinessStatus.PARTIAL.value
    assert readiness["checks"]["labeled_evaluation_groups"]["passed"] is False
    assert readiness["checks"]["cross_validation_feasibility"]["passed"] is False
    assert "Unsatisfied preconditions" in readiness["summary"]


# ------------------------------------------------------------------------------
# T11: 0 etiket varsa kesin NOT_READY.
# ------------------------------------------------------------------------------
def test_t11_zero_labels_strictly_returns_not_ready():
    """T11: assess_ml_readiness strictly returns NOT_READY when labeled count is 0."""
    ds = PatentMLDataset()
    readiness = assess_ml_readiness(ds, min_labels_required=50)

    assert readiness["status"] == ReadinessStatus.NOT_READY.value
    assert readiness["labeled_count"] == 0
    assert "NOT READY" in readiness["summary"]


# ------------------------------------------------------------------------------
# T12: Hazırlık kontrolleri sabit passed=True ile sahte güvence üretmez.
# ------------------------------------------------------------------------------
def test_t12_readiness_checks_dynamically_evaluated_no_hardcoded_true():
    """T12: Readiness checks dynamically fail when invalid formats or synthetic contamination exist."""
    ds = PatentMLDataset()
    mock_ds = PatentMLDataset.__new__(PatentMLDataset)

    # Contaminate queue with an invalid label "99"
    mock_queue = [dict(r) for r in ds.queue]
    mock_queue[0]["human_relevance_label"] = "99"
    mock_ds.queue = mock_queue

    readiness = assess_ml_readiness(mock_ds, min_labels_required=50)
    assert readiness["checks"]["zero_synthetic_labels"]["passed"] is False
    assert "Invalid synthetic label format detected" in readiness["checks"]["zero_synthetic_labels"]["detail"]


# ------------------------------------------------------------------------------
# T13: Gerçek chunk sayısı manifest ile eşleşir (256 Chunks).
# ------------------------------------------------------------------------------
def test_t13_real_chunks_count_matches_sanitized_and_data_manifests():
    """T13: Physical chunks count matches data_manifest.json and sanitized_manifest.txt."""
    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        chunks = [json.loads(line) for line in f]

    with open(DATA_MANIFEST_PATH, "r", encoding="utf-8") as f:
        data_manifest = json.load(f)
    assert len(chunks) == data_manifest["total_chunks"]
    assert len(chunks) >= 256

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest_text = f.read()
    assert f"{len(chunks)} pasaj" in manifest_text
    assert "83 pasaj" not in manifest_text, "Stale 83 chunk count found in sanitized_manifest.txt"


# ------------------------------------------------------------------------------
# T14: Patentin aile grubu güncellense de mevcut gerçek etiketi silinmez.
# ------------------------------------------------------------------------------
def test_t14_updating_patent_family_preserves_existing_human_label():
    """T14: Updating patent family assignment dynamically preserves human label on regeneration."""
    ds = PatentMLDataset()
    pair_id = "Q01_US11457576B2"
    q_first = list(ds.queries.values())[0]
    existing_labels = {
        pair_id: {
            "human_relevance_label": "1",
            "reviewer_id": "reviewer_ksu",
            "review_status": "REVIEWED",
            "review_notes": "Important art",
            "reviewed_at": "2026-11-05T12:00:00",
            "query_text": q_first["query_text"],
        }
    }

    # Simulate moving US11457576B2 from singleton into a newly discovered family
    modified_patents = []
    for p in ds.patents.values():
        p_copy = dict(p)
        if p_copy["publication_number"] == "US11457576B2":
            p_copy["family_id"] = "FAM_DISCOVERED_NEW_01"
        modified_patents.append(p_copy)

    new_queue = build_candidate_queue(
        queries=list(ds.queries.values()),
        patents=modified_patents,
        chunks=list(ds.chunks.values()),
        existing_labels=existing_labels,
    )

    rec = next(r for r in new_queue if r["pair_id"] == pair_id)
    assert rec["human_relevance_label"] == "1"
    assert rec["family_id"] == "FAM_DISCOVERED_NEW_01"
    assert rec["evaluation_group_id"] == "FAM_DISCOVERED_NEW_01"
    assert rec["review_status"] == "REVIEWED"


# ------------------------------------------------------------------------------
# T15: BM25 ve ana Streamlit uygulaması çalışmaya devam eder.
# ------------------------------------------------------------------------------
def test_t15_bm25_retrieval_and_main_streamlit_app_operational():
    """T15: BM25 search engine executes deterministically and main app renders successfully."""
    engine = BM25SearchEngine()
    results = engine.search("soil moisture sensor", top_k_patents=5)
    assert len(results) == 5
    assert results[0].bm25_score > 0.0

    main_app_path = ROOT_DIR / "app.py"
    at = AppTest.from_file(str(main_app_path), default_timeout=10)
    at.run()
    assert not at.exception, "Main Streamlit app threw an unexpected exception"


# ------------------------------------------------------------------------------
# T16: Etiketleme ekranındaki kaydetme, sıfırlama ve filtreleme davranışları bozulmaz.
# ------------------------------------------------------------------------------
def test_t16_labeling_app_full_workflow_save_clear_filter(tmp_path):
    """T16: Complete UI workflow test: filter by query, consciously select option, save, clear label."""
    app_path = ROOT_DIR / "tools" / "labeling_app.py"
    temp_file = tmp_path / "queue_t16.csv"
    shutil.copy(PROD_QUEUE_PATH, temp_file)

    at = AppTest.from_file(str(app_path), default_timeout=10)
    at.session_state["custom_queue_path"] = temp_file
    at.run()

    # 1. Filter by query Q03
    query_sb = next(sb for sb in at.sidebar.selectbox if "Sorgu Filtresi" in sb.label)
    query_sb.set_value("Q03").run()

    # 2. Select option 1
    radio = next(r for r in at.radio if "İlgililik Seviyesi" in r.label)
    radio.set_value(radio.options[1]).run()

    # 3. Save (advances index)
    save_btn = next(b for b in at.button if "Etiketi Kaydet" in b.label)
    save_btn.click().run()

    # Check disk
    store = LabelStore(queue_path=temp_file)
    recs = store.load_records()
    q03_first = next(r for r in recs if r["query_id"] == "Q03")
    assert q03_first["human_relevance_label"] == "1"

    # 4. Navigate back to previous record and clear label
    prev_btn = next(b for b in at.button if "Önceki" in b.label)
    prev_btn.click().run()

    clear_btn = next(b for b in at.button if "Sıfırla" in b.label)
    clear_btn.click().run()

    recs_after = store.load_records()
    q03_cleared = next(r for r in recs_after if r["pair_id"] == q03_first["pair_id"])
    assert q03_cleared["human_relevance_label"] == ""
    assert q03_cleared["review_status"] == "PENDING_HUMAN_REVIEW"
