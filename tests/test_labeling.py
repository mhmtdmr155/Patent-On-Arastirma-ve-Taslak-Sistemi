"""
Tests for Human Relevance Labeling Infrastructure, LabelStore, and Labeling App (PAT-0404).
Verifies candidate queue integrity, atomic persistence, validation, and UI interaction.
"""

import csv
from pathlib import Path
import shutil
import pytest
from streamlit.testing.v1 import AppTest

from src.ml.dataset import PatentMLDataset, get_evaluation_group_id
from src.ml.label_store import LabelStore, FIELDNAMES

ROOT_DIR = Path(__file__).resolve().parent.parent
QUEUE_PATH = ROOT_DIR / "data" / "annotations" / "labeling_queue.csv"
QUERIES_PATH = ROOT_DIR / "data" / "annotations" / "queries.csv"
PATENTS_PATH = ROOT_DIR / "data" / "processed" / "patents.jsonl"


# ==============================================================================
# 1. Queue Data Integrity Tests (160 Pairs, 6 Groups, Zero Fake Labels)
# ==============================================================================

def test_t01_labeling_queue_file_exists_and_header():
    """Verify labeling_queue.csv exists and has all required header columns."""
    assert QUEUE_PATH.exists(), f"Queue file not found at {QUEUE_PATH}"
    with open(QUEUE_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
    assert header == FIELDNAMES


def test_t02_labeling_queue_cardinality_and_uniqueness():
    """Verify queue cardinality matches Cartesian product (queries x patents) with 100% unique pair_ids."""
    with open(QUEUE_PATH, mode="r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    query_ids = {r["query_id"] for r in rows}
    pub_nums = {r["publication_number"] for r in rows}
    expected_count = len(query_ids) * len(pub_nums)

    assert len(rows) == expected_count, f"Expected {expected_count} pairs in queue, found {len(rows)}"
    assert len(set(r["pair_id"] for r in rows)) == expected_count, "Duplicate pair_ids found in labeling queue!"
    assert len(query_ids) == 20, f"Expected 20 unique queries, found {len(query_ids)}"
    assert len(pub_nums) >= 8, f"Expected at least 8 unique patents, found {len(pub_nums)}"

    # Ensure baseline 8 patents are present
    baseline_8 = {"US7836910B2", "US8671969B2", "US9241451B2", "US11064664B2", "US11457576B2", "US11674944B2", "US12144295B1", "US9804113B2"}
    assert baseline_8.issubset(pub_nums)


def test_t03_evaluation_group_assignment_in_queue():
    """Verify evaluation groups in queue preserve baseline lineages and prevent singleton leakage."""
    with open(QUEUE_PATH, mode="r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    eval_groups = {r["evaluation_group_id"] for r in rows}
    assert len(eval_groups) >= 6, f"Expected at least 6 evaluation groups, got {len(eval_groups)}"

    expected_baseline_groups = {
        "FAM_US_DRESSELHAUS_SOIL_01",
        "FAM_US_IRR_WIRELESS_01",
        "SINGLETON_US11457576B2",
        "SINGLETON_US11674944B2",
        "SINGLETON_US12144295B1",
        "SINGLETON_US9804113B2",
    }
    assert expected_baseline_groups.issubset(eval_groups)


def test_t04_bm25_candidate_flag_and_score_consistency():
    """Verify BM25 positive candidates and unranked candidates (score 0.0000) have consistent flags and ranks."""
    with open(QUEUE_PATH, mode="r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    candidates = [r for r in rows if r["bm25_candidate"] == "True"]
    non_candidates = [r for r in rows if r["bm25_candidate"] == "False"]

    assert len(candidates) > 0, "No positive BM25 candidates found!"
    assert len(candidates) + len(non_candidates) == len(rows)

    for r in candidates:
        score = float(r["bm25_score"])
        assert score > 0.0, f"Candidate {r['pair_id']} has non-positive score: {score}"
        assert int(r["bm25_rank"]) >= 1

    for r in non_candidates:
        score = float(r["bm25_score"])
        assert score == 0.0, f"Non-candidate {r['pair_id']} has non-zero score: {score}"
        assert r["bm25_rank"] in {"", "0"}
        assert r["evidence_chunk_id"] == ""


def test_t05_queue_human_labels_are_zero_synthetic():
    """Verify production queue has valid label format ('', '0', '1', '2') and lifecycle status consistency."""
    with open(QUEUE_PATH, mode="r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for r in rows:
        lbl = r["human_relevance_label"]
        assert lbl in {"", "0", "1", "2"}, f"Invalid label format detected in {r['pair_id']}: {lbl}"
        if lbl != "":
            assert r["review_status"] == "REVIEWED"
            assert r["reviewer_id"] != ""
            assert r["reviewed_at"] != ""
        else:
            assert r["review_status"] == "PENDING_HUMAN_REVIEW"


# ==============================================================================
# 2. LabelStore Atomic Persistence and Validation Tests
# ==============================================================================

@pytest.fixture
def temp_label_store(tmp_path):
    """Fixture providing an isolated LabelStore backed by a copy of the real queue."""
    temp_file = tmp_path / "labeling_queue_test.csv"
    shutil.copy(QUEUE_PATH, temp_file)
    store = LabelStore(queue_path=temp_file)
    return store, temp_file


def test_t06_label_store_initial_state(temp_label_store):
    """Verify LabelStore loads records and reports 0% progress initially."""
    store, _ = temp_label_store
    records = store.load_records()
    total_count = len(records)
    assert total_count >= 160

    progress = store.get_progress()
    assert progress["total"] == total_count
    assert progress["reviewed"] == 0
    assert progress["pending"] == total_count
    assert progress["percent_complete"] == 0.0
    assert progress["distribution"] == {"0": 0, "1": 0, "2": 0}


def test_t07_label_store_valid_label_updates(temp_label_store):
    """Verify updating with valid labels ('0', '1', '2') modifies record and recalculates progress."""
    store, temp_file = temp_label_store
    total_count = len(store.load_records())

    # Update first pair to 2
    ok1 = store.update_label("Q01_US7836910B2", label="2", reviewer_id="engineer_a", notes="Core prior art")
    assert ok1 is True

    # Update second pair to 1
    ok2 = store.update_label("Q01_US8671969B2", label=1, reviewer_id="engineer_b", notes="Family continuation")
    assert ok2 is True

    # Update third pair to 0
    ok3 = store.update_label("Q01_US9804113B2", label="0", reviewer_id="engineer_a", notes="Different domain")
    assert ok3 is True

    # Check updated record fields
    rec1 = store.get_record("Q01_US7836910B2")
    assert rec1 is not None
    assert rec1["human_relevance_label"] == "2"
    assert rec1["reviewer_id"] == "engineer_a"
    assert rec1["review_status"] == "REVIEWED"
    assert rec1["review_notes"] == "Core prior art"
    assert "UTC" in rec1["reviewed_at"]

    # Verify progress
    progress = store.get_progress()
    assert progress["total"] == total_count
    assert progress["reviewed"] == 3
    assert progress["pending"] == total_count - 3
    assert progress["percent_complete"] == pytest.approx(3 / total_count * 100.0, rel=1e-3)
    assert progress["distribution"] == {"0": 1, "1": 1, "2": 1}

    # Verify disk persistence across fresh store instance
    fresh_store = LabelStore(queue_path=temp_file)
    fresh_rec = fresh_store.get_record("Q01_US7836910B2")
    assert fresh_rec["human_relevance_label"] == "2"


def test_t08_label_store_invalid_label_rejection(temp_label_store):
    """Verify LabelStore raises ValueError on invalid label values."""
    store, _ = temp_label_store

    invalid_values = ["-1", "3", "5", "irrelevant", "True", None, 3, -1]
    for inv in invalid_values:
        with pytest.raises(ValueError, match="Invalid relevance label"):
            store.update_label("Q01_US7836910B2", label=inv)


def test_t09_label_store_unknown_pair_handling(temp_label_store):
    """Verify LabelStore returns False / None when referencing non-existent pair_ids."""
    store, _ = temp_label_store

    assert store.get_record("NON_EXISTENT_PAIR") is None
    assert store.update_label("NON_EXISTENT_PAIR", label="1") is False
    assert store.clear_label("NON_EXISTENT_PAIR") is False


def test_t10_label_store_clear_label(temp_label_store):
    """Verify clearing a label reverts record to pending status and updates progress."""
    store, _ = temp_label_store
    total_count = len(store.load_records())

    store.update_label("Q01_US7836910B2", label="2", reviewer_id="tester")
    assert store.get_progress()["reviewed"] == 1

    ok = store.clear_label("Q01_US7836910B2")
    assert ok is True

    rec = store.get_record("Q01_US7836910B2")
    assert rec["human_relevance_label"] == ""
    assert rec["review_status"] == "PENDING_HUMAN_REVIEW"
    assert rec["reviewer_id"] == ""
    assert rec["reviewed_at"] == ""

    assert store.get_progress()["reviewed"] == 0
    assert store.get_progress()["pending"] == total_count


def test_t11_label_store_atomic_write_no_temp_file_leakage(temp_label_store):
    """Verify that atomic writing cleans up any .tmp files."""
    store, temp_file = temp_label_store
    tmp_path = temp_file.with_suffix(".tmp")

    assert not tmp_path.exists()
    store.update_label("Q01_US7836910B2", label="1")
    assert not tmp_path.exists(), "Temporary file leaked after atomic save!"
    assert temp_file.exists()


# ==============================================================================
# 3. Streamlit Labeling Tool AppTest Interaction Tests
# ==============================================================================

def test_t12_labeling_app_renders_without_exception():
    """Verify labeling_app.py mounts cleanly with AppTest."""
    app_path = ROOT_DIR / "tools" / "labeling_app.py"
    at = AppTest.from_file(str(app_path), default_timeout=10)
    at.run()
    assert not at.exception


def test_t13_labeling_app_displays_metrics_and_first_record():
    """Verify labeling_app.py displays 4 metric boxes and the first pair's details."""
    app_path = ROOT_DIR / "tools" / "labeling_app.py"
    at = AppTest.from_file(str(app_path), default_timeout=10)
    at.run()

    # Metrics: Toplam Çift, İncelenen, Bekleyen, Tamamlanma
    metric_labels = [m.label for m in at.metric]
    assert "Toplam Çift" in metric_labels
    assert "İncelenen" in metric_labels
    assert "Bekleyen" in metric_labels
    assert "Tamamlanma" in metric_labels

    # Verify initial metric values
    total_metric = next(m for m in at.metric if m.label == "Toplam Çift")
    with open(QUEUE_PATH, mode="r", encoding="utf-8") as f:
        expected_total = len(list(csv.DictReader(f)))
    assert int(total_metric.value) == expected_total


def test_t14_labeling_app_reviewer_input_and_navigation():
    """Verify reviewer input field exists and buttons are properly wired."""
    app_path = ROOT_DIR / "tools" / "labeling_app.py"
    at = AppTest.from_file(str(app_path), default_timeout=10)
    at.run()

    # Find reviewer text input
    reviewer_input = at.text_input(key=None)
    assert reviewer_input is not None
    assert reviewer_input.value == "human_evaluator"

    # Buttons: Önceki Kayıt, Etiketi Kaydet, Sonraki Kayıt, Etiketi Sıfırla
    btn_labels = [b.label for b in at.button]
    assert any("Önceki Kayıt" in lbl for lbl in btn_labels)
    assert any("Etiketi Kaydet" in lbl for lbl in btn_labels)
    assert any("Sonraki Kayıt" in lbl for lbl in btn_labels)
    assert any("Etiketi Sıfırla" in lbl for lbl in btn_labels)


def test_t15_labeling_app_sidebar_filters():
    """Verify sidebar filters exist and allow query-level filtering."""
    app_path = ROOT_DIR / "tools" / "labeling_app.py"
    at = AppTest.from_file(str(app_path), default_timeout=10)
    at.run()

    # Radio for status filter
    status_radio = at.sidebar.radio(key=None)
    assert status_radio is not None
    assert "Yalnızca Bekleyenler" in status_radio.options

    # Selectboxes for query and patent filters
    selectboxes = at.sidebar.selectbox
    assert len(selectboxes) >= 2
    query_sb = next(sb for sb in selectboxes if "Sorgu Filtresi" in sb.label)
    assert "Tüm Sorgular" in query_sb.options
    assert "Q01" in query_sb.options
    assert "Q20" in query_sb.options

    # Filter to Q01 only
    query_sb.set_value("Q01").run()
    assert not at.exception


def test_t16_labeling_queue_no_malformed_fields():
    """Verify queue records have non-empty essential metadata and valid URLs."""
    with open(QUEUE_PATH, mode="r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for r in rows:
        assert r["pair_id"].startswith("Q")
        assert len(r["query_text"]) > 3
        assert r["publication_number"].startswith("US")
        assert len(r["patent_title"]) > 3
        assert r["source_url"].startswith("https://patents.google.com/patent/US")
        assert r["evaluation_group_id"] != ""


# ==============================================================================
# 4. End-to-End Streamlit UI Annotation & Persistence Scenarios (PAT-0404-D01)
# ==============================================================================

def test_t17_apptest_ui_save_label_0(tmp_path):
    """Scenario A: Select label 0 via Streamlit UI, save, and verify disk persistence."""
    app_path = ROOT_DIR / "tools" / "labeling_app.py"
    temp_file = tmp_path / "queue_a.csv"
    shutil.copy(QUEUE_PATH, temp_file)

    at = AppTest.from_file(str(app_path), default_timeout=10)
    at.session_state["custom_queue_path"] = temp_file
    at.run()

    radio = next(r for r in at.radio if "İlgililik" in r.label)
    radio.set_value(radio.options[0]).run()

    save_btn = next(b for b in at.button if "Etiketi Kaydet" in b.label)
    save_btn.click().run()

    rows = list(csv.DictReader(open(temp_file, encoding="utf-8")))
    assert rows[0]["human_relevance_label"] == "0"
    assert rows[0]["review_status"] == "REVIEWED"
    assert rows[0]["pair_id"].startswith("Q01_")

    # Row 1 remains pending and unlabeled
    assert rows[1]["human_relevance_label"] == ""
    assert rows[1]["review_status"] == "PENDING_HUMAN_REVIEW"


def test_t18_apptest_ui_save_label_2_and_isolation(tmp_path):
    """Scenario B: Navigate to second record, save label 2, verify record 1 is preserved."""
    app_path = ROOT_DIR / "tools" / "labeling_app.py"
    temp_file = tmp_path / "queue_b.csv"
    shutil.copy(QUEUE_PATH, temp_file)

    at = AppTest.from_file(str(app_path), default_timeout=10)
    at.session_state["custom_queue_path"] = temp_file
    at.run()

    # Save Record 0 as Label 0
    radio = next(r for r in at.radio if "İlgililik" in r.label)
    radio.set_value(radio.options[0]).run()
    next(b for b in at.button if "Etiketi Kaydet" in b.label).click().run()

    # We are now automatically on Record 1
    radio_rec1 = next(r for r in at.radio if "İlgililik" in r.label)
    radio_rec1.set_value(radio_rec1.options[2]).run()  # Option 2: Directly Relevant
    next(b for b in at.button if "Etiketi Kaydet" in b.label).click().run()

    rows = list(csv.DictReader(open(temp_file, encoding="utf-8")))
    # Verify Record 0 is still 0
    assert rows[0]["human_relevance_label"] == "0"
    assert rows[0]["pair_id"].startswith("Q01_")

    # Verify Record 1 is now 2
    assert rows[1]["human_relevance_label"] == "2"
    assert rows[1]["review_status"] == "REVIEWED"
    assert rows[1]["pair_id"].startswith("Q01_")

    # Verify Record 2 is untouched
    assert rows[2]["human_relevance_label"] == ""


def test_t19_apptest_ui_modify_existing_label(tmp_path):
    """Scenario C: Navigate back to previous record, change label to 1, verify update."""
    app_path = ROOT_DIR / "tools" / "labeling_app.py"
    temp_file = tmp_path / "queue_c.csv"
    shutil.copy(QUEUE_PATH, temp_file)

    at = AppTest.from_file(str(app_path), default_timeout=10)
    at.session_state["custom_queue_path"] = temp_file
    at.run()

    # Save Record 0 as Label 0
    radio = next(r for r in at.radio if "İlgililik" in r.label)
    radio.set_value(radio.options[0]).run()
    next(b for b in at.button if "Etiketi Kaydet" in b.label).click().run()

    # Save Record 1 as Label 2
    radio_rec1 = next(r for r in at.radio if "İlgililik" in r.label)
    radio_rec1.set_value(radio_rec1.options[2]).run()
    next(b for b in at.button if "Etiketi Kaydet" in b.label).click().run()

    # Click Previous twice to get back to Record 0
    prev_btn = next(b for b in at.button if "Önceki" in b.label)
    prev_btn.click().run()
    prev_btn = next(b for b in at.button if "Önceki" in b.label)
    prev_btn.click().run()

    # Change Record 0 label to 1
    radio_rec0 = next(r for r in at.radio if "İlgililik" in r.label)
    radio_rec0.set_value(radio_rec0.options[1]).run()
    next(b for b in at.button if "Etiketi Kaydet" in b.label).click().run()

    rows = list(csv.DictReader(open(temp_file, encoding="utf-8")))
    assert rows[0]["human_relevance_label"] == "1"
    assert rows[1]["human_relevance_label"] == "2"


def test_t20_apptest_ui_reopen_persisted_state(tmp_path):
    """Scenario D: Restart AppTest session and verify saved labels load from disk."""
    app_path = ROOT_DIR / "tools" / "labeling_app.py"
    temp_file = tmp_path / "queue_d.csv"
    shutil.copy(QUEUE_PATH, temp_file)

    # Session 1: Label two records
    store = LabelStore(queue_path=temp_file)
    store.update_label("Q01_US11674944B2", label="1", reviewer_id="user_a", notes="Partial match")
    store.update_label("Q01_US8671969B2", label="2", reviewer_id="user_a", notes="Direct continuation")

    # Session 2: Launch brand new AppTest instance
    at2 = AppTest.from_file(str(app_path), default_timeout=10)
    at2.session_state["custom_queue_path"] = temp_file
    at2.run()

    total_metric = next(m for m in at2.metric if m.label == "Toplam Çift")
    reviewed_metric = next(m for m in at2.metric if m.label == "İncelenen")
    pending_metric = next(m for m in at2.metric if m.label == "Bekleyen")

    assert int(reviewed_metric.value) == 2
    assert int(pending_metric.value) == int(total_metric.value) - 2


def test_t21_apptest_ui_clear_label_button(tmp_path):
    """Scenario E: Clear label on an annotated record and verify it reverts to pending."""
    app_path = ROOT_DIR / "tools" / "labeling_app.py"
    temp_file = tmp_path / "queue_e.csv"
    shutil.copy(QUEUE_PATH, temp_file)

    store = LabelStore(queue_path=temp_file)
    records = store.load_records()
    rec0_id = records[0]["pair_id"]
    rec1_id = records[1]["pair_id"]
    store.update_label(rec0_id, label="1", reviewer_id="user_a")
    store.update_label(rec1_id, label="2", reviewer_id="user_a")

    at = AppTest.from_file(str(app_path), default_timeout=10)
    at.session_state["custom_queue_path"] = temp_file
    at.run()

    # Clear current record (Record 0)
    clear_btn = next(b for b in at.button if "Sıfırla" in b.label)
    clear_btn.click().run()

    rows = list(csv.DictReader(open(temp_file, encoding="utf-8")))
    assert rows[0]["human_relevance_label"] == ""
    assert rows[0]["review_status"] == "PENDING_HUMAN_REVIEW"
    assert rows[1]["human_relevance_label"] == "2"

    reviewed_metric = next(m for m in at.metric if m.label == "İncelenen")
    assert int(reviewed_metric.value) == 1


def test_t22_apptest_ui_navigate_without_saving_no_leak(tmp_path):
    """Scenario F: Change radio without clicking save, navigate away, verify no ghost saving."""
    app_path = ROOT_DIR / "tools" / "labeling_app.py"
    temp_file = tmp_path / "queue_f.csv"
    shutil.copy(QUEUE_PATH, temp_file)

    at = AppTest.from_file(str(app_path), default_timeout=10)
    at.session_state["custom_queue_path"] = temp_file
    at.run()

    # Change radio on Record 0 to option 2
    radio = next(r for r in at.radio if "İlgililik" in r.label)
    radio.set_value(radio.options[2]).run()

    # Click Next WITHOUT clicking save
    next_btn = next(b for b in at.button if "Sonraki" in b.label)
    next_btn.click().run()

    # Verify disk was NOT modified for Record 0
    rows = list(csv.DictReader(open(temp_file, encoding="utf-8")))
    assert rows[0]["human_relevance_label"] == ""
    assert rows[0]["review_status"] == "PENDING_HUMAN_REVIEW"


def test_t23_apptest_ui_filter_and_save_exact_pair_id(tmp_path):
    """Scenario G: Filter by Query Q02, save label, verify only the filtered record is updated."""
    app_path = ROOT_DIR / "tools" / "labeling_app.py"
    temp_file = tmp_path / "queue_g.csv"
    shutil.copy(QUEUE_PATH, temp_file)

    at = AppTest.from_file(str(app_path), default_timeout=10)
    at.session_state["custom_queue_path"] = temp_file
    at.run()

    # Select Query Q02 in sidebar filter
    query_sb = next(sb for sb in at.sidebar.selectbox if "Sorgu Filtresi" in sb.label)
    query_sb.set_value("Q02").run()

    # Select option 2 and save
    radio = next(r for r in at.radio if "İlgililik" in r.label)
    radio.set_value(radio.options[2]).run()
    next(b for b in at.button if "Etiketi Kaydet" in b.label).click().run()

    rows = list(csv.DictReader(open(temp_file, encoding="utf-8")))

    # Verify Q01 records were untouched
    q01_rows = [r for r in rows if r["query_id"] == "Q01"]
    for r in q01_rows:
        assert r["human_relevance_label"] == ""

    # Verify first Q02 record was updated
    q02_first = next(r for r in rows if r["query_id"] == "Q02")
    assert q02_first["human_relevance_label"] == "2"
    assert q02_first["review_status"] == "REVIEWED"


def test_t24_save_atomic_error_resilience_and_tmp_cleanup(tmp_path, monkeypatch):
    """Scenario H: Simulate an os.replace failure and verify original file is preserved and .tmp is cleaned."""
    temp_file = tmp_path / "queue_h.csv"
    shutil.copy(QUEUE_PATH, temp_file)
    store = LabelStore(queue_path=temp_file)

    # Monkeypatch os.replace to simulate Windows locked file or disk error
    def mock_replace_fail(src, dst):
        raise PermissionError("Simulated Windows file lock / permission error.")

    monkeypatch.setattr("os.replace", mock_replace_fail)

    with pytest.raises(PermissionError, match="Simulated Windows file lock"):
        store.update_label("Q01_US7836910B2", label="2")

    # Verify temporary file was deleted by the finally block
    tmp_path_file = temp_file.with_suffix(".tmp")
    assert not tmp_path_file.exists(), "Leaked .tmp file after replace failure!"

    # Verify original file content was preserved
    rows = list(csv.DictReader(open(temp_file, encoding="utf-8")))
    assert len(rows) >= 160
    assert rows[0]["human_relevance_label"] == ""


def test_t25_zero_synthetic_labels_in_real_queue_preserved():
    """Verify that real production queue retains valid format and metadata consistency across all records."""
    with open(QUEUE_PATH, mode="r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) >= 160
    for r in rows:
        lbl = r.get("human_relevance_label", "")
        assert lbl in {"", "0", "1", "2"}, f"Invalid label detected: {lbl}"
        if lbl:
            assert r["review_status"] == "REVIEWED"
        else:
            assert r["review_status"] == "PENDING_HUMAN_REVIEW"


def test_t26_audit_zip_integrity_and_sanitization():
    """Verify that audit ZIP exists, is valid, and contains zero confidential/raw data."""
    import zipfile
    zip_path = ROOT_DIR / "artifacts" / "PAT-0404-D01_code_audit.zip"
    assert zip_path.exists(), f"Audit zip missing at {zip_path}"
    assert zip_path.stat().st_size > 10000

    with zipfile.ZipFile(zip_path, mode="r") as zf:
        namelist = zf.namelist()

        # Must contain essential source files
        assert "app.py" in namelist
        assert "tools/labeling_app.py" in namelist
        assert "sanitized_manifest.txt" in namelist
        assert "src/ml/label_store.py" in namelist
        assert "docs/labeling_user_guide.md" in namelist

        # Must NEVER contain forbidden or raw data
        for name in namelist:
            assert ".env" not in name
            assert not (name == ".git" or name.startswith(".git/") or name.startswith(".git\\"))
            assert not (name == ".venv" or name.startswith(".venv/") or name.startswith(".venv\\"))
            assert not name.startswith("data/raw")
            assert not name.endswith(".html")
            assert not name.endswith(".jsonl")
            assert not name.endswith("labeling_queue.csv")
            assert not name.endswith(".pyc")
            assert not name.endswith(".tmp")



