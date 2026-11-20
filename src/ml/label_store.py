"""
Atomic and Safe Label Storage Module for Human Annotations (PAT-0404).
Handles persistent, atomic updates to labeling_queue.csv to prevent data loss.
"""

import csv
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_QUEUE_PATH = ROOT_DIR / "data" / "annotations" / "labeling_queue.csv"

FIELDNAMES = [
    "pair_id",
    "query_id",
    "query_text",
    "publication_number",
    "patent_title",
    "source_url",
    "family_id",
    "evaluation_group_id",
    "bm25_score",
    "bm25_rank",
    "bm25_candidate",
    "evidence_chunk_id",
    "human_relevance_label",
    "reviewer_id",
    "review_status",
    "review_notes",
    "reviewed_at",
]


class LabelStore:
    """Manages disk-persistent human relevance labels with atomic writing."""

    def __init__(self, queue_path: Optional[Path] = None):
        self.queue_path = queue_path or DEFAULT_QUEUE_PATH

    def load_records(self) -> list[dict[str, Any]]:
        """Load all records from the queue CSV."""
        if not self.queue_path.exists():
            return []
        with open(self.queue_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def get_record(self, pair_id: str) -> Optional[dict[str, Any]]:
        """Retrieve a specific record by its unique pair_id."""
        records = self.load_records()
        for r in records:
            if r.get("pair_id") == pair_id:
                return r
        return None

    def update_label(
        self,
        pair_id: str,
        label: int | str,
        reviewer_id: str = "human_reviewer",
        notes: str = "",
    ) -> bool:
        """
        Update the human label for a specific pair_id and atomically save to disk.
        Enforces valid label values: '0', '1', '2'.
        """
        str_label = str(label).strip()
        if str_label not in {"0", "1", "2"}:
            raise ValueError(f"Invalid relevance label: '{label}'. Must be 0, 1, or 2.")

        records = self.load_records()
        target_found = False
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        for r in records:
            if r.get("pair_id") == pair_id:
                r["human_relevance_label"] = str_label
                r["reviewer_id"] = reviewer_id.strip() if reviewer_id else "human_reviewer"
                r["review_status"] = "REVIEWED"
                r["review_notes"] = notes.strip()
                r["reviewed_at"] = now_str
                target_found = True
                break

        if not target_found:
            return False

        self._save_atomic(records)
        return True

    def clear_label(self, pair_id: str) -> bool:
        """Reset a record back to pending status."""
        records = self.load_records()
        target_found = False

        for r in records:
            if r.get("pair_id") == pair_id:
                r["human_relevance_label"] = ""
                r["reviewer_id"] = ""
                r["review_status"] = "PENDING_HUMAN_REVIEW"
                r["review_notes"] = ""
                r["reviewed_at"] = ""
                target_found = True
                break

        if not target_found:
            return False

        self._save_atomic(records)
        return True

    def get_progress(self) -> dict[str, Any]:
        """Calculate annotation progress and distribution."""
        records = self.load_records()
        total = len(records)
        reviewed = 0
        distribution = {"0": 0, "1": 0, "2": 0}

        for r in records:
            lbl = str(r.get("human_relevance_label", "")).strip()
            if lbl in distribution:
                reviewed += 1
                distribution[lbl] += 1

        return {
            "total": total,
            "reviewed": reviewed,
            "pending": total - reviewed,
            "percent_complete": (reviewed / total * 100.0) if total > 0 else 0.0,
            "distribution": distribution,
        }

    def _save_atomic(self, records: list[dict[str, Any]]) -> None:
        """
        Atomically write records to disk via a temporary file replaced in-place.
        Reduces partial write or file corruption risks during process interruption.
        """
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.queue_path.with_suffix(".tmp")

        try:
            with open(tmp_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
                writer.writeheader()
                writer.writerows(records)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except (AttributeError, OSError):
                    pass

            # Atomic replacement on Windows and POSIX (same directory/filesystem)
            os.replace(tmp_path, self.queue_path)
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

