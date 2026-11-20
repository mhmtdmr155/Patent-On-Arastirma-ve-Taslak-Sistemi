"""
Numerical Feature Extraction Module for Patent Relevance Reranking (PAT-0407 & PAT-0408).
Extracts 7 interpretable, leakage-free numeric features for (Query, Patent) pairs.
"""

import math
from typing import Any, Optional
from src.retrieval.tokenizer import tokenize

TARGET_DOMAIN_CPCS = {"A01G25", "G01N33", "G01N27", "A01G", "G01N"}
FEATURE_NAMES = [
    "bm25_score_raw",
    "bm25_score_query_norm",
    "title_token_overlap",
    "abstract_token_overlap",
    "best_passage_overlap",
    "cpc_domain_match",
    "patent_word_count_norm",
]


class FeatureExtractor:
    """Extracts interpretable numerical features from (Query, Patent) pairs."""

    def __init__(self, avg_corpus_word_count: float = 7500.0):
        self.avg_corpus_word_count = max(avg_corpus_word_count, 1.0)

    def extract_features_for_pair(
        self,
        query_text: str,
        patent_record: dict[str, Any],
        raw_bm25_score: float = 0.0,
        max_query_bm25_score: float = 0.0,
        best_passage_text: Optional[str] = None,
    ) -> dict[str, float]:
        """
        Extract 7 leakage-free numerical features for a single query-patent pair.
        Never references human labels. Guaranteed finite and non-NaN.
        """
        q_tokens = set(tokenize(query_text, remove_stopwords=True))
        q_len = max(len(q_tokens), 1)

        # F1: Raw BM25 Score
        f1_raw_score = float(max(raw_bm25_score, 0.0))
        if not math.isfinite(f1_raw_score):
            f1_raw_score = 0.0

        # F2: Query-Normalized BM25 Score in [0, 1]
        denom = max(max_query_bm25_score, f1_raw_score, 1e-6)
        f2_query_norm = float(f1_raw_score / denom)
        f2_query_norm = max(0.0, min(1.0, f2_query_norm))

        # F3: Title Token Overlap
        title_text = patent_record.get("title", "") or ""
        title_tokens = set(tokenize(title_text, remove_stopwords=True))
        f3_title_overlap = len(q_tokens.intersection(title_tokens)) / q_len

        # F4: Abstract Token Overlap
        abstract_text = patent_record.get("abstract", "") or ""
        abstract_tokens = set(tokenize(abstract_text, remove_stopwords=True))
        f4_abstract_overlap = len(q_tokens.intersection(abstract_tokens)) / q_len

        # F5: Best Evidence Passage Token Overlap
        if best_passage_text:
            passage_tokens = set(tokenize(best_passage_text, remove_stopwords=True))
            f5_passage_overlap = len(q_tokens.intersection(passage_tokens)) / q_len
        else:
            f5_passage_overlap = 0.0

        # F6: CPC Pilot Domain Affinity Count (Target Domain Class Match)
        # Note: Measures how many CPC codes of the patent belong to the target agricultural
        # and soil sensor domain (A01G, G01N). This represents domain priority / pilot domain affinity,
        # not a query-to-CPC similarity (as queries do not possess formal patent classifications).
        patent_cpcs = patent_record.get("cpc_codes", []) or []
        cpc_matches = 0
        for cpc in patent_cpcs:
            clean_cpc = cpc.replace("/", "").replace(" ", "").upper()
            for target in TARGET_DOMAIN_CPCS:
                if clean_cpc.startswith(target):
                    cpc_matches += 1
                    break
        f6_cpc_match = float(min(cpc_matches, 5.0))  # Capped at 5.0

        # F7: Normalized Patent Word Count (Tariff Depth)
        # Note: Normalized against avg_corpus_word_count. During cross-validation,
        # this baseline average must be computed strictly from the training fold corpus.
        desc_text = patent_record.get("description", "") or ""
        total_words = len(desc_text.split()) + len(abstract_text.split())
        f7_word_count_norm = float(total_words / self.avg_corpus_word_count)

        features = {
            "bm25_score_raw": round(f1_raw_score, 4),
            "bm25_score_query_norm": round(f2_query_norm, 4),
            "title_token_overlap": round(f3_title_overlap, 4),
            "abstract_token_overlap": round(f4_abstract_overlap, 4),
            "best_passage_overlap": round(f5_passage_overlap, 4),
            "cpc_domain_match": round(f6_cpc_match, 4),
            "patent_word_count_norm": round(f7_word_count_norm, 4),
        }

        # Safety assertion: all values finite
        for k, v in features.items():
            if not math.isfinite(v):
                features[k] = 0.0

        return features

    def to_vector(self, feature_dict: dict[str, float]) -> list[float]:
        """Convert feature dictionary to ordered float list according to FEATURE_NAMES."""
        return [float(feature_dict.get(name, 0.0)) for name in FEATURE_NAMES]

