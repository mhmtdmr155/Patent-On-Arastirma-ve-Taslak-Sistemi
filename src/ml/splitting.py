"""
Cross-Validation Splitting and Data Leakage Prevention Module (PAT-0405 & PAT-0406).
Implements family-aware and query-aware GroupKFold splitting and strict leakage checks.
"""

from typing import Any, Generator
import numpy as np
from sklearn.model_selection import GroupKFold
from sklearn.feature_extraction.text import TfidfVectorizer


def family_aware_kfold_split(
    records: list[dict[str, Any]],
    n_splits: int = 3,
) -> Generator[tuple[list[int], list[int]], None, None]:
    """
    Generate train/test index splits grouped strictly by evaluation_group_id.
    Ensures that members of the same patent family NEVER appear in both train and test.
    """
    groups = [r["evaluation_group_id"] for r in records]
    unique_groups = len(set(groups))

    if unique_groups < n_splits:
        raise ValueError(
            f"Cannot split into {n_splits} folds with only {unique_groups} unique evaluation groups."
        )

    gkf = GroupKFold(n_splits=n_splits)
    dummy_X = np.zeros(len(records))

    for train_idx, test_idx in gkf.split(dummy_X, groups=groups):
        # Strict programmatic verification of zero group leakage
        train_groups = {groups[i] for i in train_idx}
        test_groups = {groups[i] for i in test_idx}
        leakage = train_groups.intersection(test_groups)
        if leakage:
            raise RuntimeError(f"Family group leakage detected between train and test: {leakage}")

        yield list(train_idx), list(test_idx)


def query_aware_kfold_split(
    records: list[dict[str, Any]],
    n_splits: int = 4,
) -> Generator[tuple[list[int], list[int]], None, None]:
    """
    Generate train/test index splits grouped strictly by query_id.
    Evaluates model generalization to previously unseen technical search queries.
    """
    groups = [r["query_id"] for r in records]
    unique_groups = len(set(groups))

    if unique_groups < n_splits:
        raise ValueError(
            f"Cannot split into {n_splits} folds with only {unique_groups} unique queries."
        )

    gkf = GroupKFold(n_splits=n_splits)
    dummy_X = np.zeros(len(records))

    for train_idx, test_idx in gkf.split(dummy_X, groups=groups):
        # Strict programmatic verification of zero query leakage
        train_queries = {groups[i] for i in train_idx}
        test_queries = {groups[i] for i in test_idx}
        leakage = train_queries.intersection(test_queries)
        if leakage:
            raise RuntimeError(f"Query leakage detected between train and test: {leakage}")

        yield list(train_idx), list(test_idx)


def fit_transform_tfidf_no_leakage(
    train_texts: list[str],
    test_texts: list[str],
    max_features: int = 50,
) -> tuple[np.ndarray, np.ndarray, TfidfVectorizer]:
    """
    Fit TfidfVectorizer strictly on train_texts, then transform test_texts.
    Guarantees no test vocabulary or IDF statistics leak into the training representation.
    """
    vectorizer = TfidfVectorizer(max_features=max_features, lowercase=True)
    X_train = vectorizer.fit_transform(train_texts).toarray()
    X_test = vectorizer.transform(test_texts).toarray()
    return X_train, X_test, vectorizer

