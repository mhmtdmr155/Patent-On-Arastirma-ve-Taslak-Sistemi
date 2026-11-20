"""
Safety, Anti-Data-Loss, and ML Readiness Integrity Verification Suite (PAT-0404-D03).
Validates:
1. ML readiness false-READY bug fix: pending records cannot trigger READY.
2. Label data loss prevention: query text change safety, retired patent retention, duplicate pair_id rejection.
3. Queue regeneration idempotency and atomic writes.
4. Single main execution guard in generate_labeling_queue.py.
5. Git ignore protection of human annotations and private reviews.
"""

import csv
import os
import shutil
import subprocess
import sys
from pathlib import Path
import pytest

from src.ml.dataset import PatentMLDataset
from src.ml.readiness import assess_ml_readiness, ReadinessStatus
from scripts.generate_labeling_queue import (
    load_existing_annotations,
    build_candidate_queue,
    generate_queue,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
PROD_QUEUE_PATH = ROOT_DIR / "data" / "annotations" / "labeling_queue.csv"
QUERIES_PATH = ROOT_DIR / "data" / "annotations" / "queries.csv"


# ==============================================================================
# 01 — ML Readiness Security Fixes
# ==============================================================================

def test_readiness_pending_records_with_labels_strictly_not_ready():
    """
    ChatGPT Bug Reproduction: 160 records with labels '0' and '1', but review_status
    is PENDING_HUMAN_REVIEW and reviewer_id/reviewed_at are empty.
    MUST return NOT_READY and 0 validated human labels.
    """
    ds = PatentMLDataset()
    mock_ds = PatentMLDataset.__new__(PatentMLDataset)
    mock_queue = [dict(r) for r in ds.queue]

    for i in range(len(mock_queue)):
        mock_queue[i]["human_relevance_label"] = "1" if i % 2 == 0 else "0"
        mock_queue[i]["review_status"] = "PENDING_HUMAN_REVIEW"
        mock_queue[i]["reviewer_id"] = ""
        mock_queue[i]["reviewed_at"] = ""

    mock_ds.queue = mock_queue

    readiness = assess_ml_readiness(mock_ds)
    assert readiness["status"] == ReadinessStatus.NOT_READY.value
    assert readiness["labeled_count"] == 0
    assert "NOT READY" in readiness["summary"]

    # Lifecycle consistency check must also fail
    assert readiness["checks"]["metadata_lifecycle_consistency"]["passed"] is False


def test_readiness_empty_label_with_reviewed_status_rejected():
    """Records with empty label but review_status=REVIEWED must fail lifecycle consistency."""
    ds = PatentMLDataset()
    mock_ds = PatentMLDataset.__new__(PatentMLDataset)
    mock_queue = [dict(r) for r in ds.queue]

    # Malformed row: empty label marked as REVIEWED
    mock_queue[0]["human_relevance_label"] = ""
    mock_queue[0]["review_status"] = "REVIEWED"
    mock_ds.queue = mock_queue

    readiness = assess_ml_readiness(mock_ds)
    assert readiness["checks"]["metadata_lifecycle_consistency"]["passed"] is False
    assert "empty label with status REVIEWED" in readiness["checks"]["metadata_lifecycle_consistency"]["detail"]


def test_readiness_checks_count_and_scientific_naming():
    """Assess readiness contains exactly the documented 10 preconditions with scientific naming."""
    ds = PatentMLDataset()
    readiness = assess_ml_readiness(ds)
    checks = readiness["checks"]

    expected_checks = [
        "sufficient_human_labels",
        "class_diversity",
        "query_coverage",
        "evaluation_groups_valid",
        "candidate_pool_complete",
        "label_format_and_scale_validity",
        "labeled_evaluation_groups",
        "metadata_lifecycle_consistency",
        "cross_validation_feasibility",
        "zero_pending_contamination",
    ]
    for chk in expected_checks:
        assert chk in checks, f"Missing expected readiness check: {chk}"

    # Verify zero_synthetic_labels alias exists for backwards compatibility
    assert "zero_synthetic_labels" in checks


# ==============================================================================
# 02 — Anti-Data-Loss Queue Generation Tests (Tests A through F)
# ==============================================================================

def test_a_query_text_change_stops_or_preserves_without_loss():
    """Test A: When query text changes for an already annotated pair, aborts safely or preserves label."""
    ds = PatentMLDataset()
    pair_id = "Q01_US11674944B2"
    existing_labels = {
        pair_id: {
            "pair_id": pair_id,
            "query_id": "Q01",
            "query_text": "original query text for soil moisture",
            "publication_number": "US11674944B2",
            "patent_title": "Soil Sensor",
            "human_relevance_label": "2",
            "reviewer_id": "annotator_1",
            "review_status": "REVIEWED",
            "review_notes": "Key reference",
            "reviewed_at": "2026-11-05T12:00:00",
        }
    }

    # Query text in queries has changed
    modified_queries = [dict(list(ds.queries.values())[0])]
    modified_queries[0]["query_text"] = "completely altered new query text"

    # Default abort_on_query_change=True must raise RuntimeError
    with pytest.raises(RuntimeError, match="CRITICAL SAFETY STOP: Query text for 'Q01' changed"):
        build_candidate_queue(
            queries=modified_queries,
            patents=list(ds.patents.values()),
            existing_labels=existing_labels,
            abort_on_query_change=True,
        )

    # When explicit preservation is enabled, label is NEVER wiped
    queue_preserved = build_candidate_queue(
        queries=modified_queries,
        patents=list(ds.patents.values()),
        existing_labels=existing_labels,
        abort_on_query_change=False,
    )
    rec = next(r for r in queue_preserved if r["pair_id"] == pair_id)
    assert rec["human_relevance_label"] == "2"
    assert rec["review_status"] == "REVIEWED"
    assert "QUERY TEXT MODIFIED" in rec["review_notes"]


def test_b_retired_patent_preserves_human_annotation():
    """Test B: When a patent is removed from active corpus, its existing human annotations are retained."""
    ds = PatentMLDataset()
    pair_id = "Q01_RETIRED_PATENT_01"
    existing_labels = {
        pair_id: {
            "pair_id": pair_id,
            "query_id": "Q01",
            "query_text": list(ds.queries.values())[0]["query_text"],
            "publication_number": "US0000001B2",
            "patent_title": "Retired Irrigation Valve",
            "human_relevance_label": "1",
            "reviewer_id": "reviewer_ksu",
            "review_status": "REVIEWED",
            "review_notes": "Valuable historical art",
            "reviewed_at": "2026-11-05T10:00:00",
        }
    }

    # Generate queue with active patents (US0000001B2 is NOT in active patents)
    queue = build_candidate_queue(
        queries=list(ds.queries.values()),
        patents=list(ds.patents.values()),
        existing_labels=existing_labels,
    )

    retained = [r for r in queue if r["pair_id"] == pair_id]
    assert len(retained) == 1, "Retired annotated pair was silently dropped!"
    assert retained[0]["human_relevance_label"] == "1"
    assert retained[0]["review_status"] == "REVIEWED"
    assert "RETAINED HISTORICAL ANNOTATION" in retained[0]["review_notes"]


def test_c_duplicate_pair_id_rejected():
    """Test C: Duplicate pair_id generation strictly raises ValueError."""
    ds = PatentMLDataset()
    # Provide duplicate patents with same publication_number
    duplicate_patents = [list(ds.patents.values())[0], list(ds.patents.values())[0]]

    with pytest.raises(ValueError, match="Duplicate pair_id generated"):
        build_candidate_queue(
            queries=list(ds.queries.values()),
            patents=duplicate_patents,
        )


def test_d_queue_regeneration_idempotency(tmp_path):
    """Test D: Re-running generate_queue twice leaves record count and annotations unchanged."""
    temp_file = tmp_path / "idempotent_queue.csv"
    shutil.copy(PROD_QUEUE_PATH, temp_file)

    # First run
    count1 = generate_queue(queue_path=temp_file)
    with open(temp_file, "r", encoding="utf-8") as f:
        rows1 = list(csv.DictReader(f))

    # Second run
    count2 = generate_queue(queue_path=temp_file)
    with open(temp_file, "r", encoding="utf-8") as f:
        rows2 = list(csv.DictReader(f))

    assert count1 == count2
    assert len(rows1) == len(rows2)
    assert rows1 == rows2


def test_e_corrupt_csv_aborts_without_overwriting(tmp_path):
    """Test E: Malformed CSV raises RuntimeError and disk file remains intact."""
    corrupt_file = tmp_path / "malformed_queue.csv"
    corrupt_file.write_text("invalid_col1,invalid_col2\nfoo,bar\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="CRITICAL SAFETY STOP"):
        generate_queue(queue_path=corrupt_file)

    # Original content preserved
    assert "invalid_col1,invalid_col2" in corrupt_file.read_text(encoding="utf-8")


def test_f_expansion_preserves_existing_labels(tmp_path):
    """Test F: Adding new patents preserves existing human labels and creates pending pairs for new patents."""
    temp_file = tmp_path / "expand_queue.csv"
    shutil.copy(PROD_QUEUE_PATH, temp_file)

    # Add a human label to first record
    rows = list(csv.DictReader(open(temp_file, encoding="utf-8")))
    rows[0]["human_relevance_label"] = "2"
    rows[0]["review_status"] = "REVIEWED"
    rows[0]["reviewer_id"] = "annotator_ksu"
    rows[0]["reviewed_at"] = "2026-11-05T12:00:00"

    with open(temp_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # Regenerate queue
    generate_queue(queue_path=temp_file)

    rows_after = list(csv.DictReader(open(temp_file, encoding="utf-8")))
    assert rows_after[0]["human_relevance_label"] == "2"
    assert rows_after[0]["review_status"] == "REVIEWED"
    assert rows_after[0]["reviewer_id"] == "annotator_ksu"


# ==============================================================================
# 03 — Duplicate Main Guard & CLI Subprocess Test
# ==============================================================================

def test_generate_labeling_queue_cli_single_execution():
    """Verify scripts/generate_labeling_queue.py executes exactly once when invoked from CLI."""
    script_path = ROOT_DIR / "scripts" / "generate_labeling_queue.py"

    # Count __name__ == '__main__' occurrences in source file
    content = script_path.read_text(encoding="utf-8")
    main_count = content.count('if __name__ == "__main__":')
    assert main_count == 1, f"Found {main_count} occurrences of main guard in {script_path}; expected exactly 1."

    # Run as subprocess
    res = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        cwd=str(ROOT_DIR),
    )
    assert res.returncode == 0
    assert "Done. Candidate pairs count:" in res.stdout
    # Ensure it only ran once (Done appears only once)
    assert res.stdout.count("Done. Candidate pairs count:") == 1


# ==============================================================================
# 04 — Git Protection of Human Annotations
# ==============================================================================

def test_gitignore_protects_human_annotations():
    """Verify that labeling_queue.csv and backup CSVs are strictly git-ignored while queries.csv is tracked."""
    cmd_queue = ["git", "check-ignore", "data/annotations/labeling_queue.csv"]
    res_queue = subprocess.run(cmd_queue, capture_output=True, text=True, cwd=str(ROOT_DIR))
    assert res_queue.returncode == 0, "data/annotations/labeling_queue.csv MUST be git-ignored!"

    cmd_backup = ["git", "check-ignore", "data/annotations/backup_labels.csv"]
    res_backup = subprocess.run(cmd_backup, capture_output=True, text=True, cwd=str(ROOT_DIR))
    assert res_backup.returncode == 0, "Backup annotation CSVs MUST be git-ignored!"

    cmd_queries = ["git", "check-ignore", "data/annotations/queries.csv"]
    res_queries = subprocess.run(cmd_queries, capture_output=True, text=True, cwd=str(ROOT_DIR))
    assert res_queries.returncode != 0, "data/annotations/queries.csv must NOT be git-ignored (remains in version control)!"

