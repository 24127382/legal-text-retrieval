"""Load and inspect the raw LegalIR, LegalQA, and corpus data."""

from .audit import audit_corpus, audit_cross_task, audit_legal_ir, audit_legal_qa
from .loaders import load_corpus, load_legal_ir, load_legal_qa

__all__ = [
    "audit_corpus",
    "audit_cross_task",
    "audit_legal_ir",
    "audit_legal_qa",
    "load_corpus",
    "load_legal_ir",
    "load_legal_qa",
]
