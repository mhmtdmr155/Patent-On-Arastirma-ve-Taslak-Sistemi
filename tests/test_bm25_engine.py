"""Unit and integration tests for BM25 retrieval engine and tokenizer (PAT-0301 to PAT-0305).

Validates tokenization determinism, technical identifier preservation, BM25Okapi
scoring, passage-to-patent max aggregation, tie-breaking, and top-candidate bounds (T11-T29).
"""

import math
from pathlib import Path
import pytest

from src.retrieval.bm25_engine import BM25SearchEngine, SearchResult
from src.retrieval.tokenizer import tokenize

ROOT_DIR = Path(__file__).resolve().parent.parent
CHUNKS_PATH = ROOT_DIR / "data" / "processed" / "chunks.jsonl"
PATENTS_PATH = ROOT_DIR / "data" / "processed" / "patents.jsonl"


# -----------------------------------------------------------------------------
# TOKENIZER TESTS (T11 - T15)
# -----------------------------------------------------------------------------

def test_t11_tokenizer_deterministic():
    """T11: Identical input strings produce identical token sequences."""
    text = "Smart soil moisture sensor with capacitive probe."
    tokens1 = tokenize(text)
    tokens2 = tokenize(text)
    assert tokens1 == tokens2
    assert tokens1 == ["smart", "soil", "moisture", "sensor", "capacitive", "probe"]


def test_t12_tokenizer_case_normalization():
    """T12: Case differences are normalized to lowercase."""
    t1 = tokenize("Soil Moisture SENSOR")
    t2 = tokenize("soil moisture sensor")
    assert t1 == t2


def test_t13_tokenizer_preserves_technical_identifiers():
    """T13: Preserves CPC codes, circuit terms, units, and patent IDs."""
    text = "RLC circuit with 5V DC and 100pF in US11457576B2 under A01G25/16."
    tokens = tokenize(text)
    assert "rlc" in tokens
    assert "circuit" in tokens
    assert "5v" in tokens
    assert "dc" in tokens
    assert "100pf" in tokens
    assert "us11457576b2" in tokens
    assert "a01g25/16" in tokens


def test_t14_tokenizer_empty_and_none():
    """T14: Empty, whitespace, or None inputs safely return empty lists."""
    assert tokenize("") == []
    assert tokenize("   ") == []
    assert tokenize(None) == []


def test_t15_query_and_corpus_share_same_tokenizer():
    """T15: Verifies tokenizer used for search query matches indexing tokenizer."""
    engine = BM25SearchEngine()
    sample_chunk_text = engine.chunks[0]["text"]
    chunk_tokens = tokenize(sample_chunk_text)
    assert chunk_tokens == engine.tokenized_corpus[0]


# -----------------------------------------------------------------------------
# BM25 ENGINE TESTS (T16 - T29)
# -----------------------------------------------------------------------------

def test_t16_real_corpus_loads():
    """T16: Verifies real chunks and patent metadata load from disk."""
    import json
    engine = BM25SearchEngine()
    manifest_path = Path(__file__).resolve().parent.parent / "data_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert len(engine.chunks) == manifest["total_chunks"]
        assert len(engine.patent_metadata_map) == manifest["total_patents"]
    else:
        assert len(engine.chunks) >= 256
        assert len(engine.patent_metadata_map) >= 8
    assert engine.is_indexed


def test_t17_bm25_initialized():
    """T17: Verifies BM25Okapi instance is created."""
    engine = BM25SearchEngine()
    assert engine.bm25 is not None
    assert len(engine.bm25.doc_len) == len(engine.chunks)


def test_t18_matching_query_produces_positive_scores():
    """T18: Terms present in corpus produce strictly positive, finite scores."""
    engine = BM25SearchEngine()
    results = engine.search("soil moisture sensor", top_k_patents=5)
    assert len(results) > 0
    for r in results:
        assert r.bm25_score > 0.0
        assert math.isfinite(r.bm25_score)


def test_t19_non_matching_query_returns_empty():
    """T19: Terms completely absent from the corpus return 0 results (no false matches)."""
    engine = BM25SearchEngine()
    results = engine.search("quantum blockchain cryptocurrency teleportation")
    assert results == []


def test_t20_patent_aggregation_deduplicates_publication_numbers():
    """T20: Aggregates multiple chunks per patent into unique publication results."""
    engine = BM25SearchEngine()
    results = engine.search("irrigation control methods and systems", top_k_patents=20)
    pubs = [r.publication_number for r in results]
    assert len(pubs) == len(set(pubs)), f"Duplicate publication numbers found: {pubs}"


def test_t21_t22_top_k_bounds():
    """T21, T22: Result count is bounded by min(matching_patents, top_k_patents)."""
    engine = BM25SearchEngine()
    results_20 = engine.search("soil", top_k_patents=20)
    assert len(results_20) <= len(engine.patent_metadata_map)
    assert len(results_20) <= 20

    # When requesting top 3
    results_3 = engine.search("soil", top_k_patents=3)
    assert len(results_3) == 3


def test_t23_top_5_results_structure():
    """T23: Verifies search results contain all required attribution fields."""
    engine = BM25SearchEngine()
    results = engine.search("series RLC circuit", top_k_patents=5)
    assert len(results) > 0

    top = results[0]
    assert isinstance(top, SearchResult)
    assert top.publication_number == "US9804113B2"
    assert top.ranking_method == "BM25"
    assert len(top.best_passage) > 20
    assert top.best_section in {"ABSTRACT", "DESCRIPTION", "BACKGROUND", "TITLE"}
    assert top.chunk_id.startswith("US9804113B2")
    assert top.source_url.startswith("https://patents.google.com/patent/")
    assert len(top.top_passages) >= 1


def test_t24_deterministic_tie_breaking():
    """T24: Identical query produces deterministic ordered results across runs."""
    engine = BM25SearchEngine()
    q = "automatic irrigation"
    run1 = [r.publication_number for r in engine.search(q)]
    run2 = [r.publication_number for r in engine.search(q)]
    assert run1 == run2


def test_t25_source_url_integrity():
    """T25: Every search result provides a valid source URL."""
    engine = BM25SearchEngine()
    results = engine.search("sensor", top_k_patents=5)
    for r in results:
        assert r.source_url == f"https://patents.google.com/patent/{r.publication_number}/en"


def test_t26_best_chunk_id_accuracy():
    """T26: Chunk ID references the patent publication number."""
    engine = BM25SearchEngine()
    results = engine.search("valve controller", top_k_patents=5)
    for r in results:
        assert r.chunk_id.startswith(r.publication_number)


def test_t27_scores_are_finite_numbers():
    """T27: Verifies all BM25 scores are finite floating point values."""
    engine = BM25SearchEngine()
    results = engine.search("soil moisture sensor", top_k_patents=8)
    for r in results:
        assert isinstance(r.bm25_score, float)
        assert not math.isnan(r.bm25_score)
        assert not math.isinf(r.bm25_score)


def test_t28_corrupt_chunks_path_raises_error(tmp_path):
    """T28: Verifies engine raises appropriate error if chunks file is missing or corrupt."""
    non_existent = tmp_path / "does_not_exist.jsonl"
    with pytest.raises(FileNotFoundError):
        BM25SearchEngine(chunks_path=non_existent)


def test_t29_empty_query_returns_empty_list():
    """T29: Empty or whitespace query safely returns empty list without scoring."""
    engine = BM25SearchEngine()
    assert engine.search("") == []
    assert engine.search("   ") == []

