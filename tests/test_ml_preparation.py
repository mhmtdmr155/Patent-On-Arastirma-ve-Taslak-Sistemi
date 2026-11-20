"""
Tests for Machine Learning Feature Extraction, Train/Test Splitting, and Readiness Assessment (PAT-0405 to PAT-0409).
Validates feature mathematical bounds, GroupKFold leakage prevention, TF-IDF containment, and NOT_READY status.
"""

import math
from pathlib import Path
import pytest
import numpy as np

from src.ml.dataset import PatentMLDataset, get_evaluation_group_id
from src.ml.features import FeatureExtractor, FEATURE_NAMES
from src.ml.splitting import (
    family_aware_kfold_split,
    query_aware_kfold_split,
    fit_transform_tfidf_no_leakage,
)
from src.ml.readiness import assess_ml_readiness, ReadinessStatus

ROOT_DIR = Path(__file__).resolve().parent.parent


# ==============================================================================
# 1. Dataset & Annotation Entity Coordination
# ==============================================================================

def test_t01_ml_dataset_loading():
    """Verify PatentMLDataset coordinates queries, patents, and candidate queue rows."""
    ds = PatentMLDataset()
    assert len(ds.queries) == 20
    assert len(ds.patents) in [8, 34]
    assert len(ds.queue) == len(ds.queries) * len(ds.patents)
    assert len(ds.chunks) > 0

    assert len(ds.get_labeled_pairs()) == 0
    assert len(ds.get_unlabeled_pairs()) == len(ds.queue)


def test_t02_binary_label_mapping():
    """Verify mapping policy: 0 -> 0, 1 -> 1, 2 -> 1, invalid/unlabeled -> None."""
    ds = PatentMLDataset()
    assert ds.map_to_binary_label("0") == 0
    assert ds.map_to_binary_label(0) == 0

    assert ds.map_to_binary_label("1") == 1
    assert ds.map_to_binary_label(1) == 1

    assert ds.map_to_binary_label("2") == 1
    assert ds.map_to_binary_label(2) == 1

    # Invalid / empty
    assert ds.map_to_binary_label("") is None
    assert ds.map_to_binary_label(None) is None
    assert ds.map_to_binary_label("3") is None
    assert ds.map_to_binary_label("unlabeled") is None


def test_t03_evaluation_group_id_helper():
    """Verify multi-patent families share family ID while singletons get distinct SINGLETON_{pub}."""
    # Multi-patent families
    assert get_evaluation_group_id("US7836910B2") == "FAM_US_DRESSELHAUS_SOIL_01"
    assert get_evaluation_group_id("US8671969B2") == "FAM_US_DRESSELHAUS_SOIL_01"
    assert get_evaluation_group_id("US9241451B2") == "FAM_US_IRR_WIRELESS_01"
    assert get_evaluation_group_id("US11064664B2") == "FAM_US_IRR_WIRELESS_01"

    # Singletons
    assert get_evaluation_group_id("US11457576B2") == "SINGLETON_US11457576B2"
    assert get_evaluation_group_id("US11674944B2") == "SINGLETON_US11674944B2"
    assert get_evaluation_group_id("US12144295B1") == "SINGLETON_US12144295B1"
    assert get_evaluation_group_id("US9804113B2") == "SINGLETON_US9804113B2"


# ==============================================================================
# 2. Numerical Feature Extraction (PAT-0407 & PAT-0408)
# ==============================================================================

def test_t04_feature_extraction_all_160_pairs_finite_and_bounded():
    """Verify FeatureExtractor produces 7 finite, non-negative, bounded features for all 160 pairs."""
    ds = PatentMLDataset()
    fe = FeatureExtractor(avg_corpus_word_count=7500.0)

    for row in ds.queue:
        q_text = row["query_text"]
        pub_num = row["publication_number"]
        patent = ds.get_patent(pub_num)
        assert patent is not None

        raw_score = float(row.get("bm25_score", 0.0))
        ev_chunk_id = row.get("evidence_chunk_id")
        best_passage = ds.get_chunk(ev_chunk_id).get("text", "") if ev_chunk_id else None

        features = fe.extract_features_for_pair(
            query_text=q_text,
            patent_record=patent,
            raw_bm25_score=raw_score,
            max_query_bm25_score=7.0,
            best_passage_text=best_passage,
        )

        # 1. Feature keys check
        assert list(features.keys()) == FEATURE_NAMES

        # 2. Vector conversion check
        vec = fe.to_vector(features)
        assert len(vec) == 7

        # 3. All values finite and bounded
        for k, v in features.items():
            assert math.isfinite(v), f"Feature {k} is not finite: {v}"
            assert v >= 0.0, f"Feature {k} is negative: {v}"

        assert 0.0 <= features["bm25_score_query_norm"] <= 1.0
        assert 0.0 <= features["title_token_overlap"] <= 1.0
        assert 0.0 <= features["abstract_token_overlap"] <= 1.0
        assert 0.0 <= features["best_passage_overlap"] <= 1.0
        assert 0.0 <= features["cpc_domain_match"] <= 5.0
        assert features["patent_word_count_norm"] > 0.0


def test_t05_feature_extractor_robustness_on_edge_cases():
    """Verify FeatureExtractor handles empty strings, None passages, and zero denominators safely."""
    fe = FeatureExtractor(avg_corpus_word_count=0.0)  # zero word count handled safely
    empty_patent = {"title": "", "abstract": "", "description": "", "cpc_codes": []}

    features = fe.extract_features_for_pair(
        query_text="",
        patent_record=empty_patent,
        raw_bm25_score=-5.0,  # negative score clamped
        max_query_bm25_score=0.0,
        best_passage_text=None,
    )

    assert features["bm25_score_raw"] == 0.0
    assert features["bm25_score_query_norm"] == 0.0
    assert features["title_token_overlap"] == 0.0
    assert features["abstract_token_overlap"] == 0.0
    assert features["best_passage_overlap"] == 0.0
    assert features["cpc_domain_match"] == 0.0
    assert features["patent_word_count_norm"] == 0.0

    for v in features.values():
        assert math.isfinite(v)


def test_t06_zero_target_leakage_in_features():
    """Verify feature extractor signature never accepts or accesses ground truth labels."""
    fe = FeatureExtractor()
    import inspect
    sig = inspect.signature(fe.extract_features_for_pair)
    param_names = set(sig.parameters.keys())

    forbidden = {"label", "human_label", "relevance", "review_status", "ground_truth", "target"}
    assert param_names.isdisjoint(forbidden), f"Target label parameter detected in FeatureExtractor: {param_names.intersection(forbidden)}"


# ==============================================================================
# 3. Train/Test Splitting & Leakage Prevention (PAT-0405 & PAT-0406)
# ==============================================================================

def test_t07_family_aware_kfold_splits_zero_leakage():
    """Verify GroupKFold across evaluation groups produces 0 family leakage across all folds."""
    ds = PatentMLDataset()
    splits = list(family_aware_kfold_split(ds.queue, n_splits=3))
    assert len(splits) == 3

    for fold_idx, (train_idx, test_idx) in enumerate(splits):
        assert len(train_idx) > 0
        assert len(test_idx) > 0
        assert len(set(train_idx).intersection(set(test_idx))) == 0

        train_groups = {ds.queue[i]["evaluation_group_id"] for i in train_idx}
        test_groups = {ds.queue[i]["evaluation_group_id"] for i in test_idx}

        # Zero group overlap
        group_leak = train_groups.intersection(test_groups)
        assert len(group_leak) == 0, f"Fold {fold_idx} has evaluation group leakage: {group_leak}"

        # Family continuation containment
        train_patents = {ds.queue[i]["publication_number"] for i in train_idx}
        test_patents = {ds.queue[i]["publication_number"] for i in test_idx}

        # Dresselhaus family
        d_pats = {"US7836910B2", "US8671969B2"}
        assert d_pats.issubset(train_patents) or d_pats.issubset(test_patents), f"Fold {fold_idx} split Dresselhaus family!"

        # Irrigation controller family
        i_pats = {"US9241451B2", "US11064664B2"}
        assert i_pats.issubset(train_patents) or i_pats.issubset(test_patents), f"Fold {fold_idx} split Wireless Irrigation family!"


def test_t08_query_aware_kfold_splits_zero_leakage():
    """Verify GroupKFold across queries produces 0 query leakage across all folds."""
    ds = PatentMLDataset()
    splits = list(query_aware_kfold_split(ds.queue, n_splits=4))
    assert len(splits) == 4

    for fold_idx, (train_idx, test_idx) in enumerate(splits):
        train_queries = {ds.queue[i]["query_id"] for i in train_idx}
        test_queries = {ds.queue[i]["query_id"] for i in test_idx}

        query_leak = train_queries.intersection(test_queries)
        assert len(query_leak) == 0, f"Fold {fold_idx} has query leakage: {query_leak}"
        assert len(test_queries) == 5  # 20 queries / 4 folds = 5 queries per fold


def test_t09_splitting_insufficient_groups_error():
    """Verify splitting raises ValueError when requesting more splits than available groups."""
    ds = PatentMLDataset()
    groups = set(r["evaluation_group_id"] for r in ds.queue)
    excess_splits = len(groups) + 5
    with pytest.raises(ValueError, match="Cannot split into"):
        list(family_aware_kfold_split(ds.queue, n_splits=excess_splits))

    with pytest.raises(ValueError, match="Cannot split into 25 folds"):
        list(query_aware_kfold_split(ds.queue, n_splits=25))


def test_t10_fit_transform_tfidf_no_leakage():
    """Verify TF-IDF fit occurs strictly on training texts with test terms excluded from vocabulary."""
    train_texts = [
        "soil moisture sensor irrigation controller",
        "wireless soil sensor probe monitoring",
    ]
    test_texts = [
        "autonomous drone crop health multispectral imaging",
        "soil moisture sensor system",
    ]

    X_train, X_test, vectorizer = fit_transform_tfidf_no_leakage(train_texts, test_texts, max_features=10)

    vocab = set(vectorizer.vocabulary_.keys())
    assert "moisture" in vocab
    assert "sensor" in vocab

    # Unseen test terms MUST NOT appear in vocabulary
    test_only_terms = {"drone", "autonomous", "multispectral", "imaging", "crop", "health"}
    assert vocab.isdisjoint(test_only_terms), f"Test vocabulary leaked into TF-IDF: {vocab.intersection(test_only_terms)}"

    assert X_train.shape[0] == 2
    assert X_test.shape[0] == 2
    assert X_train.shape[1] == len(vocab)
    assert X_test.shape[1] == len(vocab)


# ==============================================================================
# 4. ML Readiness Assessment (PAT-0404 & PAT-0409)
# ==============================================================================

def test_t11_ml_readiness_current_dataset_strictly_not_ready():
    """Verify readiness audit reports NOT_READY on current dataset with 0 human annotations."""
    ds = PatentMLDataset()
    readiness = assess_ml_readiness(ds, min_labels_required=50)

    assert readiness["status"] == ReadinessStatus.NOT_READY.value
    assert readiness["labeled_count"] == 0
    assert readiness["min_required"] == 50
    assert "NOT READY" in readiness["summary"]

    checks = readiness["checks"]
    assert checks["sufficient_human_labels"]["passed"] is False
    assert checks["class_diversity"]["passed"] is False
    assert checks["query_coverage"]["passed"] is False
    assert checks["evaluation_groups_valid"]["passed"] is True
    assert checks["candidate_pool_complete"]["passed"] is True
    assert checks["zero_synthetic_labels"]["passed"] is True


def test_t12_ml_readiness_partial_and_ready_transitions():
    """Verify readiness transition logic using mock in-memory dataset instances."""
    ds = PatentMLDataset()

    # Create mock dataset with 10 verified labels (insufficient count -> PARTIAL)
    mock_ds_partial = PatentMLDataset.__new__(PatentMLDataset)
    mock_queue_partial = [dict(r) for r in ds.queue]
    for i in range(10):
        mock_queue_partial[i]["human_relevance_label"] = "1" if i % 2 == 0 else "0"
        mock_queue_partial[i]["review_status"] = "REVIEWED"
        mock_queue_partial[i]["reviewer_id"] = "reviewer_test"
        mock_queue_partial[i]["reviewed_at"] = "2026-11-05T12:00:00"
    mock_ds_partial.queue = mock_queue_partial

    readiness_part = assess_ml_readiness(mock_ds_partial, min_labels_required=50)
    assert readiness_part["status"] == ReadinessStatus.PARTIAL.value
    assert readiness_part["labeled_count"] == 10

    # Create mock dataset with 60 balanced labels across >=5 queries
    mock_ds_ready = PatentMLDataset.__new__(PatentMLDataset)
    mock_queue_ready = [dict(r) for r in ds.queue]
    # Pick indices across at least 5 distinct queries
    queries_seen = set()
    labeled_indices = []
    for idx, r in enumerate(mock_queue_ready):
        qid = r["query_id"]
        if len(labeled_indices) < 60:
            labeled_indices.append(idx)
            queries_seen.add(qid)
        elif len(queries_seen) < 5 and qid not in queries_seen:
            labeled_indices.append(idx)
            queries_seen.add(qid)

    for count, i in enumerate(labeled_indices):
        mock_queue_ready[i]["human_relevance_label"] = "2" if count % 3 == 0 else ("1" if count % 3 == 1 else "0")
        mock_queue_ready[i]["review_status"] = "REVIEWED"
        mock_queue_ready[i]["reviewer_id"] = "reviewer_test"
        mock_queue_ready[i]["reviewed_at"] = "2026-11-05T12:00:00"
    mock_ds_ready.queue = mock_queue_ready

    readiness_ready = assess_ml_readiness(mock_ds_ready, min_labels_required=50)
    assert readiness_ready["status"] == ReadinessStatus.READY.value
    assert readiness_ready["labeled_count"] >= 60


def test_t13_cpc_domain_affinity_definition_and_bounds():
    """Verify Feature 6 (cpc_domain_match) measures patent target domain affinity capped at 5."""
    fe = FeatureExtractor()

    # Zero domain matches
    patent_irrelevant_cpc = {"title": "X", "abstract": "Y", "description": "Z", "cpc_codes": ["H04L29/06", "B60R16/02"]}
    f_zero = fe.extract_features_for_pair("soil moisture", patent_irrelevant_cpc)
    assert f_zero["cpc_domain_match"] == 0.0

    # Two domain matches
    patent_two_cpcs = {"title": "X", "abstract": "Y", "description": "Z", "cpc_codes": ["A01G25/16", "G01N33/24"]}
    f_two = fe.extract_features_for_pair("soil moisture", patent_two_cpcs)
    assert f_two["cpc_domain_match"] == 2.0

    # Six domain matches (must be capped at 5.0)
    many_cpcs = ["A01G25/00", "A01G25/16", "G01N33/24", "G01N27/04", "A01G", "G01N"]
    patent_many = {"title": "X", "abstract": "Y", "description": "Z", "cpc_codes": many_cpcs}
    f_capped = fe.extract_features_for_pair("unrelated query terms", patent_many)
    assert f_capped["cpc_domain_match"] == 5.0


