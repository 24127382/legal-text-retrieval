"""Lexical retrieval baselines and local diagnostics."""

from .bm25 import build_bm25, lexical_tokenize, retrieve_bm25
from .evaluation import diagnose_dev_rankings, evaluate_retrieval
from .split import make_legalir_split, select_samples

__all__ = [
    "build_bm25",
    "diagnose_dev_rankings",
    "evaluate_retrieval",
    "lexical_tokenize",
    "make_legalir_split",
    "retrieve_bm25",
    "select_samples",
]
