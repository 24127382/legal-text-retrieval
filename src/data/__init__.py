"""Raw competition data schemas, loaders, and read-only audits."""

from .audit import (
    audit_all,
    audit_corpus,
    audit_cross_task,
    audit_legal_ir,
    audit_legal_qa,
    fingerprint_path,
    save_report,
)
from .loaders import DataSchemaError, load_corpus, load_legal_ir, load_legal_qa
from .schemas import MISSING, CorpusDocument, LegalIRSample, LegalQASample, is_missing

__all__ = [
    "MISSING",
    "CorpusDocument",
    "DataSchemaError",
    "LegalIRSample",
    "LegalQASample",
    "audit_all",
    "audit_corpus",
    "audit_cross_task",
    "audit_legal_ir",
    "audit_legal_qa",
    "fingerprint_path",
    "is_missing",
    "load_corpus",
    "load_legal_ir",
    "load_legal_qa",
    "save_report",
]
