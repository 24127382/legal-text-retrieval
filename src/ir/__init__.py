"""Lexical retrieval baselines and local diagnostics."""

from .bm25 import build_bm25, lexical_tokenize, retrieve_bm25
from .evaluation import evaluate_retrieval

__all__ = ["build_bm25", "evaluate_retrieval", "lexical_tokenize", "retrieve_bm25"]
