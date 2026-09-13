"""Lexical retrieval baselines and local diagnostics."""

from .aggregate import AGGREGATION_METHODS, aggregate_documents
from .bm25 import (
    build_bm25,
    lexical_tokenize,
    retrieve_bm25,
    retrieve_bm25_aggregations,
)
from .evaluation import (
    compare_official_style_top_5,
    diagnose_dev_rankings,
    evaluate_candidate_pool,
    evaluate_retrieval,
    make_legalir_predictions,
    summarize_first_gold_ranks,
)
from .split import make_legalir_split, select_samples

__all__ = [
    "AGGREGATION_METHODS",
    "aggregate_documents",
    "build_bm25",
    "compare_official_style_top_5",
    "diagnose_dev_rankings",
    "evaluate_candidate_pool",
    "evaluate_retrieval",
    "lexical_tokenize",
    "make_legalir_predictions",
    "make_legalir_split",
    "retrieve_bm25",
    "retrieve_bm25_aggregations",
    "select_samples",
    "summarize_first_gold_ranks",
]
