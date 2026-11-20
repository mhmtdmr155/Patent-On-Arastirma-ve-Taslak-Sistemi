"""Patent Retrieval Module (PAT-0301 to PAT-0307).

Provides deterministic tokenization, BM25Okapi passage indexing, patent-level
score aggregation, and Top-20 / Top-5 source-attributed candidate selection.
"""

from src.retrieval.tokenizer import tokenize
from src.retrieval.bm25_engine import BM25SearchEngine, SearchResult

__all__ = ["tokenize", "BM25SearchEngine", "SearchResult"]

