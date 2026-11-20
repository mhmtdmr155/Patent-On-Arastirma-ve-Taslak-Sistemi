"""BM25 Passage Indexing and Patent Retrieval Engine (PAT-0302 to PAT-0305).

Utilizes rank-bm25 (BM25Okapi) to index section-aware passage chunks from data/processed/chunks.jsonl,
aggregates passage scores to patent level via max-pooling, and delivers source-attributed Top-20
candidates and Top-5 user-facing results.
"""

from dataclasses import asdict, dataclass, field
import json
import math
from pathlib import Path
from typing import Any, Optional

from rank_bm25 import BM25Okapi

from src.retrieval.tokenizer import tokenize


@dataclass
class SearchResult:
    """Attributed patent search result with passage provenance (PAT-0305)."""
    publication_number: str
    application_number: Optional[str]
    title: str
    bm25_score: float
    ranking_method: str = "BM25"
    best_passage: str = ""
    best_section: str = ""
    chunk_id: str = ""
    internal_chunk_locator: str = ""
    source_document_locator: Optional[str] = None
    source_url: str = ""
    cpc_codes: list[str] = field(default_factory=list)
    top_passages: list[dict[str, Any]] = field(default_factory=list)
    inventors: list[str] = field(default_factory=list)
    assignee: Optional[str] = None
    total_matching_patents: int = 0

    @property
    def score(self) -> float:
        """Alias for bm25_score."""
        return self.bm25_score

    def to_dict(self) -> dict[str, Any]:
        """Convert dataclass to dictionary."""
        d = asdict(self)
        d["score"] = self.bm25_score
        return d


class BM25SearchEngine:
    """In-memory BM25Okapi search engine operating on section-aware passage chunks."""

    def __init__(self, chunks_path: Optional[Path] = None, patents_path: Optional[Path] = None):
        root_dir = Path(__file__).resolve().parent.parent.parent
        self.chunks_path = chunks_path or (root_dir / "data" / "processed" / "chunks.jsonl")
        self.patents_path = patents_path or (root_dir / "data" / "processed" / "patents.jsonl")

        self.chunks: list[dict[str, Any]] = []
        self.tokenized_corpus: list[list[str]] = []
        self.bm25: Optional[BM25Okapi] = None
        self.patent_metadata_map: dict[str, dict[str, Any]] = {}
        self.is_indexed = False

        self._load_and_index()

    def _load_and_index(self) -> None:
        """Load chunks and patents from disk and build the BM25Okapi index."""
        if not self.chunks_path.exists():
            raise FileNotFoundError(f"Chunks corpus not found at {self.chunks_path}. Run pipeline first.")

        # Load patent metadata for fast lookup
        if self.patents_path.exists():
            for line in self.patents_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                p_data = json.loads(line)
                self.patent_metadata_map[p_data["publication_number"]] = p_data

        # Load chunks
        self.chunks = []
        self.tokenized_corpus = []

        chunk_ids_seen = set()
        for line_num, line in enumerate(self.chunks_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            chunk = json.loads(line)

            cid = chunk.get("chunk_id")
            if not cid or cid in chunk_ids_seen:
                raise ValueError(f"Invalid or duplicate chunk_id at line {line_num}: {cid}")
            chunk_ids_seen.add(cid)

            text = chunk.get("text", "").strip()
            if not text:
                raise ValueError(f"Empty text in chunk {cid} at line {line_num}")

            tokens = tokenize(text, remove_stopwords=True)
            self.chunks.append(chunk)
            self.tokenized_corpus.append(tokens)

        if not self.chunks:
            raise ValueError(f"No valid chunks loaded from {self.chunks_path}")

        # Initialize rank-bm25 BM25Okapi model
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        self.is_indexed = True

    def search(
        self,
        query: str,
        top_k_patents: int = 20,
        max_passages_per_patent: int = 3,
    ) -> list[SearchResult]:
        """
        Execute BM25 search across all passage chunks, aggregate scores to patent level
        using max-pooling (patent_score = max(passage_scores)), and return distinct patent results.
        """
        if not self.is_indexed or not self.bm25:
            raise RuntimeError("BM25 index is not initialized.")

        query_tokens = tokenize(query, remove_stopwords=True)
        if not query_tokens:
            return []

        # Get raw BM25 scores for all passage chunks
        passage_scores = self.bm25.get_scores(query_tokens)

        # Group matching passages by publication_number
        # Only consider passages with strictly positive score (score > 0.0)
        patent_matches: dict[str, list[tuple[float, dict[str, Any]]]] = {}

        for score, chunk in zip(passage_scores, self.chunks):
            # Check for finite score and positive match
            if not math.isfinite(score) or score <= 0.0:
                continue

            pub = chunk["publication_number"]
            if pub not in patent_matches:
                patent_matches[pub] = []
            patent_matches[pub].append((float(score), chunk))

        if not patent_matches:
            return []

        # Aggregate at patent level using max-pooling
        # Rationale: A patent document is as relevant to a technical query as its most relevant passage.
        patent_aggregated: list[tuple[float, str, list[tuple[float, dict[str, Any]]]]] = []

        for pub, matches in patent_matches.items():
            # Sort matches for this patent descending by passage score
            matches.sort(key=lambda x: x[0], reverse=True)
            max_score = matches[0][0]
            patent_aggregated.append((max_score, pub, matches))

        # Sort patents:
        # Primary: BM25 score descending
        # Secondary (Tie-breaker): publication_number ascending for determinism
        patent_aggregated.sort(key=lambda x: (-x[0], x[1]))

        # Limit to top_k distinct patents (PAT-0304)
        selected_patents = patent_aggregated[:top_k_patents]

        results: list[SearchResult] = []
        for max_score, pub, matches in selected_patents:
            p_meta = self.patent_metadata_map.get(pub, {})
            best_chunk = matches[0][1]

            top_passages_list = [
                {
                    "chunk_id": m[1]["chunk_id"],
                    "section": m[1]["section"],
                    "score": round(m[0], 4),
                    "text": m[1]["text"],
                    "internal_chunk_locator": m[1].get("internal_chunk_locator", m[1].get("source_locator", "")),
                    "source_document_locator": m[1].get("source_document_locator"),
                }
                for m in matches[:max_passages_per_patent]
            ]

            res = SearchResult(
                publication_number=pub,
                application_number=p_meta.get("application_number"),
                title=p_meta.get("title", best_chunk.get("text", "")[:60]),
                bm25_score=round(max_score, 4),
                ranking_method="BM25",
                best_passage=best_chunk["text"],
                best_section=best_chunk["section"],
                chunk_id=best_chunk["chunk_id"],
                internal_chunk_locator=best_chunk.get("internal_chunk_locator", best_chunk.get("source_locator", "")),
                source_document_locator=best_chunk.get("source_document_locator"),
                source_url=best_chunk.get("source_url", f"https://patents.google.com/patent/{pub}/en"),
                cpc_codes=p_meta.get("cpc_codes", []),
                top_passages=top_passages_list,
                inventors=p_meta.get("inventors", []),
                assignee=p_meta.get("assignee"),
                total_matching_patents=len(patent_aggregated),
            )
            results.append(res)

        return results

