"""Read-only diagnostics for raw LegalIR, LegalQA, and corpus snapshots."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

from .loaders import load_corpus, load_legal_ir, load_legal_qa
from .schemas import MISSING, CorpusDocument, LegalIRSample, LegalQASample


def _sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def fingerprint_path(path: str | Path) -> dict[str, Any]:
    """Fingerprint a file or a deterministic snapshot of a directory."""

    input_path = Path(path)
    if input_path.is_file():
        digest, size = _sha256_file(input_path)
        return {
            "kind": "file",
            "path": str(input_path),
            "size_bytes": size,
            "sha256": digest,
        }
    if input_path.is_dir():
        digest = hashlib.sha256()
        files = sorted(candidate for candidate in input_path.rglob("*") if candidate.is_file())
        total_size = 0
        for file_path in files:
            relative = file_path.relative_to(input_path).as_posix()
            file_digest, size = _sha256_file(file_path)
            total_size += size
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            digest.update(str(size).encode("ascii"))
            digest.update(b"\0")
            digest.update(file_digest.encode("ascii"))
            digest.update(b"\n")
        return {
            "kind": "directory",
            "path": str(input_path),
            "file_count": len(files),
            "size_bytes": total_size,
            "sha256": digest.hexdigest(),
        }
    raise FileNotFoundError(f"Cannot fingerprint missing path: {input_path}")


def _percentile(sorted_values: Sequence[int], probability: float) -> float | int | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    result = sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * weight
    return int(result) if result.is_integer() else round(result, 10)


def _length_statistics(values: Iterable[str]) -> dict[str, Any]:
    lengths = sorted(len(value) for value in values)
    count = len(lengths)
    return {
        "unit": "Python Unicode code points (len)",
        "p95_method": "linear interpolation at (n - 1) * 0.95",
        "count": count,
        "min": lengths[0] if lengths else None,
        "median": _percentile(lengths, 0.5),
        "mean": (sum(lengths) / count) if count else None,
        "p95": _percentile(lengths, 0.95),
        "max": lengths[-1] if lengths else None,
    }


def _duplicate_ids(values: Iterable[str]) -> list[dict[str, Any]]:
    counts = Counter(values)
    return [
        {"sample_id": sample_id, "count": count}
        for sample_id, count in sorted(counts.items())
        if count > 1
    ]


def _question_groups(
    samples: Sequence[LegalIRSample | LegalQASample],
) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for sample in samples:
        if isinstance(sample.question, str) and sample.question != "":
            groups[sample.question].append(sample.sample_id)
    return groups


def _duplicate_question_groups(
    samples: Sequence[LegalIRSample | LegalQASample],
) -> list[dict[str, Any]]:
    groups = _question_groups(samples)
    result = []
    for question, sample_ids in groups.items():
        if len(sample_ids) > 1:
            result.append(
                {
                    "sha256": hashlib.sha256(question.encode("utf-8")).hexdigest(),
                    "question": question,
                    "count": len(sample_ids),
                    "sample_ids": sample_ids,
                }
            )
    return sorted(result, key=lambda group: (group["sha256"], group["sample_ids"]))


def _audit_dataset(
    samples: Sequence[LegalIRSample | LegalQASample],
) -> dict[str, Any]:
    sample_ids = [sample.sample_id for sample in samples]
    string_questions = [
        sample.question for sample in samples if isinstance(sample.question, str)
    ]
    duplicate_questions = _duplicate_question_groups(samples)
    return {
        "sample_count": len(samples),
        "unique_sample_id_count": len(set(sample_ids)),
        "duplicate_sample_ids": _duplicate_ids(sample_ids),
        "missing_question_count": sum(sample.question is MISSING for sample in samples),
        "null_question_count": sum(sample.question is None for sample in samples),
        "empty_question_count": sum(sample.question == "" for sample in samples),
        "question_character_length": _length_statistics(string_questions),
        "exact_duplicate_non_empty_question_group_count": len(duplicate_questions),
        "exact_duplicate_non_empty_question_groups": duplicate_questions,
    }


def audit_legal_ir(
    samples: Sequence[LegalIRSample],
    corpus: Sequence[CorpusDocument] | None = None,
) -> dict[str, Any]:
    """Audit LegalIR records and optionally resolve gold IDs against a corpus."""

    gold_lists = [sample.answer for sample in samples if isinstance(sample.answer, list)]
    length_distribution = Counter(len(answer) for answer in gold_lists)
    duplicate_gold_ids = []
    unique_gold_ids: set[str] = set()
    for sample in samples:
        if not isinstance(sample.answer, list):
            continue
        unique_gold_ids.update(sample.answer)
        duplicates = {
            document_id: count
            for document_id, count in sorted(Counter(sample.answer).items())
            if count > 1
        }
        if duplicates:
            duplicate_gold_ids.append(
                {"sample_id": sample.sample_id, "duplicate_document_ids": duplicates}
            )

    resolution: dict[str, Any]
    if corpus is None:
        resolution = {
            "checked": False,
            "match_policy": "gold string == decimal corpus integer rendered with str",
            "unresolved_unique_document_id_count": None,
            "unresolved_document_ids": None,
            "samples_with_unresolved_gold": None,
        }
    else:
        corpus_ids = {str(document.id) for document in corpus}
        unresolved_ids = sorted(unique_gold_ids - corpus_ids)
        affected = []
        for sample in samples:
            if isinstance(sample.answer, list):
                unresolved_for_sample = sorted(set(sample.answer) - corpus_ids)
                if unresolved_for_sample:
                    affected.append(
                        {
                            "sample_id": sample.sample_id,
                            "unresolved_document_ids": unresolved_for_sample,
                        }
                    )
        resolution = {
            "checked": True,
            "match_policy": "gold string == decimal corpus integer rendered with str",
            "unresolved_unique_document_id_count": len(unresolved_ids),
            "unresolved_document_ids": unresolved_ids,
            "samples_with_unresolved_gold": affected,
        }

    return {
        "dataset": _audit_dataset(samples),
        "gold": {
            "missing_answer_count": sum(sample.answer is MISSING for sample in samples),
            "null_answer_count": sum(sample.answer is None for sample in samples),
            "gold_document_count_distribution": {
                str(length): count for length, count in sorted(length_distribution.items())
            },
            "empty_gold_list_count": sum(answer == [] for answer in gold_lists),
            "duplicate_document_ids_within_gold_lists": duplicate_gold_ids,
            "unique_gold_document_id_count": len(unique_gold_ids),
            "corpus_resolution": resolution,
        },
    }


def audit_legal_qa(samples: Sequence[LegalQASample]) -> dict[str, Any]:
    """Audit LegalQA records without changing answer text."""

    string_answers = [sample.answer for sample in samples if isinstance(sample.answer, str)]
    return {
        "dataset": _audit_dataset(samples),
        "answers": {
            "missing_answer_count": sum(sample.answer is MISSING for sample in samples),
            "null_answer_count": sum(sample.answer is None for sample in samples),
            "empty_answer_count": sum(sample.answer == "" for sample in samples),
            "answer_character_length": _length_statistics(string_answers),
        },
    }


def audit_corpus(documents: Sequence[CorpusDocument]) -> dict[str, Any]:
    """Audit raw corpus records, including empty passages rather than dropping them."""

    id_counts = Counter(document.id for document in documents)
    duplicate_document_ids = [
        {"document_id": document_id, "count": count}
        for document_id, count in sorted(id_counts.items())
        if count > 1
    ]

    passage_groups: dict[str, list[int]] = defaultdict(list)
    string_passages = []
    for document in documents:
        if isinstance(document.passage, str):
            string_passages.append(document.passage)
            if document.passage != "":
                passage_groups[document.passage].append(document.id)

    duplicate_passages = []
    for passage, document_ids in passage_groups.items():
        if len(document_ids) > 1:
            duplicate_passages.append(
                {
                    "sha256": hashlib.sha256(passage.encode("utf-8")).hexdigest(),
                    "character_length": len(passage),
                    "count": len(document_ids),
                    "document_ids": sorted(document_ids),
                }
            )

    return {
        "document_count": len(documents),
        "unique_document_id_count": len(id_counts),
        "duplicate_document_ids": duplicate_document_ids,
        "missing_passage_count": sum(document.passage is MISSING for document in documents),
        "null_passage_count": sum(document.passage is None for document in documents),
        "empty_passage_count": sum(document.passage == "" for document in documents),
        "missing_name_count": sum(document.name is MISSING for document in documents),
        "null_name_count": sum(document.name is None for document in documents),
        "empty_name_count": sum(document.name == "" for document in documents),
        "passage_character_length": _length_statistics(string_passages),
        "exact_duplicate_non_empty_passage_group_count": len(duplicate_passages),
        "exact_duplicate_non_empty_passage_groups": sorted(
            duplicate_passages, key=lambda group: (group["sha256"], group["document_ids"])
        ),
    }


def audit_cross_task(
    legal_ir: Sequence[LegalIRSample],
    legal_qa: Sequence[LegalQASample],
) -> dict[str, Any]:
    """Report structural overlaps without treating them as semantic pairings."""

    shared_sample_ids = sorted(
        {sample.sample_id for sample in legal_ir}
        & {sample.sample_id for sample in legal_qa}
    )
    ir_questions = _question_groups(legal_ir)
    qa_questions = _question_groups(legal_qa)
    shared_questions = set(ir_questions) & set(qa_questions)

    cardinality_counts = Counter(
        {
            "one_to_one": 0,
            "one_to_many": 0,
            "many_to_one": 0,
            "many_to_many": 0,
        }
    )
    groups = []
    for question in shared_questions:
        ir_ids = ir_questions[question]
        qa_ids = qa_questions[question]
        if len(ir_ids) == 1 and len(qa_ids) == 1:
            cardinality = "one_to_one"
        elif len(ir_ids) == 1:
            cardinality = "one_to_many"
        elif len(qa_ids) == 1:
            cardinality = "many_to_one"
        else:
            cardinality = "many_to_many"
        cardinality_counts[cardinality] += 1
        groups.append(
            {
                "sha256": hashlib.sha256(question.encode("utf-8")).hexdigest(),
                "question": question,
                "cardinality": cardinality,
                "legal_ir_sample_ids": ir_ids,
                "legal_qa_sample_ids": qa_ids,
            }
        )

    return {
        "interpretation_warning": (
            "Exact question equality is a structural observation, not evidence that "
            "LegalIR and LegalQA samples are semantically paired."
        ),
        "sample_id_overlap": {
            "count": len(shared_sample_ids),
            "sample_ids": shared_sample_ids,
        },
        "exact_non_empty_question_text_overlap": {
            "cardinality_direction": "LegalIR:LegalQA",
            "unique_shared_question_count": len(shared_questions),
            "legal_ir_sample_occurrence_count": sum(
                len(ir_questions[question]) for question in shared_questions
            ),
            "legal_qa_sample_occurrence_count": sum(
                len(qa_questions[question]) for question in shared_questions
            ),
            "cardinality_counts": dict(cardinality_counts),
            "groups": sorted(groups, key=lambda group: group["sha256"]),
        },
    }


def audit_all(
    *,
    legal_ir_path: str | Path,
    legal_qa_path: str | Path,
    corpus_path: str | Path,
) -> dict[str, Any]:
    """Load and audit one raw snapshot using caller-provided paths."""

    legal_ir = load_legal_ir(legal_ir_path)
    legal_qa = load_legal_qa(legal_qa_path)
    corpus = load_corpus(corpus_path)
    return {
        "report_schema_version": 1,
        "fingerprints": {
            "legal_ir": fingerprint_path(legal_ir_path),
            "legal_qa": fingerprint_path(legal_qa_path),
            "corpus": fingerprint_path(corpus_path),
        },
        "legal_ir": audit_legal_ir(legal_ir, corpus),
        "legal_qa": audit_legal_qa(legal_qa),
        "corpus": audit_corpus(corpus),
        "cross_task": audit_cross_task(legal_ir, legal_qa),
    }


def save_report(report: dict[str, Any], path: str | Path) -> None:
    """Serialize an audit report as readable UTF-8 JSON."""

    output_path = Path(path)
    with output_path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
