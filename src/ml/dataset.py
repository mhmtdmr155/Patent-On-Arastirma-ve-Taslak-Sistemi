"""
Patent ML Dataset and Annotation Loading Module (PAT-0404 & PAT-0405).
Coordinates queries, patent records, passage chunks, and candidate pairs.
"""

import csv
import json
from pathlib import Path
from typing import Any, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
QUERIES_PATH = ROOT_DIR / "data" / "annotations" / "queries.csv"
QUEUE_PATH = ROOT_DIR / "data" / "annotations" / "labeling_queue.csv"
PATENTS_PATH = ROOT_DIR / "data" / "processed" / "patents.jsonl"
CHUNKS_PATH = ROOT_DIR / "data" / "processed" / "chunks.jsonl"

VERIFIED_FAMILIES = {
    # Dresselhaus soil moisture sensor continuation family (Rain Bird Corp)
    "US7836910B2": "FAM_US_DRESSELHAUS_SOIL_01",
    "US8104498B2": "FAM_US_DRESSELHAUS_SOIL_01",
    "US8671969B2": "FAM_US_DRESSELHAUS_SOIL_01",
    # Ersavas / Rain Bird wireless irrigation control continuation family
    "US8849461B2": "FAM_US_IRR_WIRELESS_01",
    "US9241451B2": "FAM_US_IRR_WIRELESS_01",
    "US10716269B2": "FAM_US_IRR_WIRELESS_01",
    "US11064664B2": "FAM_US_IRR_WIRELESS_01",
    # Acclima TDR moisture sensor CIP family
    "US6657443B2": "FAM_US_ACCLIMA_TDR_01",
    "US6831468B2": "FAM_US_ACCLIMA_TDR_01",
}


def get_evaluation_group_id(publication_number: str, family_id: Optional[str] = None) -> str:
    """
    Returns the evaluation group ID for train/test splitting.
    Multi-patent families share their family_id, while independent patents
    receive a unique SINGLETON_{pub} to prevent spurious cluster leakage.
    Supports dynamic family_id for corpus expansion, or fallback to VERIFIED_FAMILIES.
    """
    pub = publication_number.strip().upper()
    if family_id and str(family_id).strip():
        return str(family_id).strip()
    if pub in VERIFIED_FAMILIES:
        return VERIFIED_FAMILIES[pub]
    return f"SINGLETON_{pub}"


class PatentMLDataset:
    """In-memory dataset coordinating queries, patents, chunks, and annotation pairs."""

    def __init__(
        self,
        queries_path: Optional[Path] = None,
        queue_path: Optional[Path] = None,
        patents_path: Optional[Path] = None,
        chunks_path: Optional[Path] = None,
    ):
        self.queries_path = queries_path or QUERIES_PATH
        self.queue_path = queue_path or QUEUE_PATH
        self.patents_path = patents_path or PATENTS_PATH
        self.chunks_path = chunks_path or CHUNKS_PATH

        self.queries: dict[str, dict[str, Any]] = {}
        self.patents: dict[str, dict[str, Any]] = {}
        self.chunks: dict[str, dict[str, Any]] = {}
        self.queue: list[dict[str, Any]] = []

        self._load_all()

    def _load_all(self) -> None:
        """Load all underlying data files if they exist."""
        # 1. Patents
        if self.patents_path.exists():
            for line in self.patents_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                p = json.loads(line)
                self.patents[p["publication_number"]] = p

        # 2. Chunks
        if self.chunks_path.exists():
            for line in self.chunks_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                c = json.loads(line)
                self.chunks[c["chunk_id"]] = c

        # 3. Queries
        if self.queries_path.exists():
            with open(self.queries_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.queries[row["query_id"]] = row

        # 4. Labeling Queue
        if self.queue_path.exists():
            with open(self.queue_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                self.queue = list(reader)

    def get_query(self, query_id: str) -> Optional[dict[str, Any]]:
        return self.queries.get(query_id)

    def get_patent(self, publication_number: str) -> Optional[dict[str, Any]]:
        return self.patents.get(publication_number)

    def get_chunk(self, chunk_id: str) -> Optional[dict[str, Any]]:
        return self.chunks.get(chunk_id)

    def get_labeled_pairs(self, strict_lifecycle: bool = True) -> list[dict[str, Any]]:
        """
        Return pairs that have received valid human annotations.
        If strict_lifecycle is True (default), strictly requires:
          - human_relevance_label in {'0', '1', '2'}
          - review_status == 'REVIEWED'
          - non-empty reviewer_id
          - non-empty reviewed_at
        """
        if not strict_lifecycle:
            return [r for r in self.queue if str(r.get("human_relevance_label", "")).strip() in {"0", "1", "2"}]

        return [
            r for r in self.queue
            if str(r.get("human_relevance_label", "")).strip() in {"0", "1", "2"}
            and str(r.get("review_status", "")).strip() == "REVIEWED"
            and bool(str(r.get("reviewer_id", "")).strip())
            and bool(str(r.get("reviewed_at", "")).strip())
        ]

    def get_unlabeled_pairs(self) -> list[dict[str, Any]]:
        """Return pending candidate pairs."""
        return [r for r in self.queue if not str(r.get("human_relevance_label", "")).strip()]

    def map_to_binary_label(self, raw_label: Any) -> Optional[int]:
        """
        Map 3-level relevance grade (0, 1, 2) to binary classification target:
        0 (Irrelevant) -> 0
        1 (Partially Relevant) -> 1
        2 (Directly Relevant) -> 1
        Returns None if unlabeled or invalid.
        """
        s = str(raw_label).strip()
        if s == "0":
            return 0
        if s in {"1", "2"}:
            return 1
        return None

