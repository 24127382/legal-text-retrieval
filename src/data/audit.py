"""Useful, read-only diagnostics for raw LegalIR, LegalQA, and corpus data."""

from collections import Counter, defaultdict

import numpy as np


def _length_statistics(texts: list[str]) -> dict:
    if not texts:
        return {"min": None, "median": None, "mean": None, "p95": None, "max": None}

    lengths = np.array([len(text) for text in texts])
    return {
        "min": int(lengths.min()),
        "median": float(np.median(lengths)),
        "mean": float(lengths.mean()),
        "p95": float(np.percentile(lengths, 95)),
        "max": int(lengths.max()),
    }


def _question_groups(samples: dict) -> dict[str, list[str]]:
    groups = defaultdict(list)
    for sample_id, sample in samples.items():
        question = sample.get("question")
        if isinstance(question, str) and question != "":
            groups[question].append(sample_id)
    return groups


def _question_audit(samples: dict) -> dict:
    questions = [
        sample["question"]
        for sample in samples.values()
        if isinstance(sample.get("question"), str)
    ]
    return {
        "sample_count": len(samples),
        "missing_question_count": sum(
            "question" not in sample for sample in samples.values()
        ),
        "null_question_count": sum(
            sample.get("question") is None and "question" in sample
            for sample in samples.values()
        ),
        "empty_question_count": sum(
            sample.get("question") == "" for sample in samples.values()
        ),
        "question_character_length": _length_statistics(questions),
    }


def audit_legal_ir(samples: dict, corpus: list[dict] | None = None) -> dict:
    """Report LegalIR question, gold-label, and optional corpus-resolution issues."""

    report = _question_audit(samples)
    gold_lists = [
        sample["answer"]
        for sample in samples.values()
        if isinstance(sample.get("answer"), list)
    ]
    unique_gold_ids = {document_id for answer in gold_lists for document_id in answer}

    duplicate_gold_ids = []
    for sample_id, sample in samples.items():
        answer = sample.get("answer")
        if not isinstance(answer, list):
            continue
        duplicates = [
            document_id
            for document_id, count in Counter(answer).items()
            if count > 1
        ]
        if duplicates:
            duplicate_gold_ids.append(
                {"sample_id": sample_id, "document_ids": duplicates}
            )

    report.update(
        {
            "missing_answer_count": sum(
                "answer" not in sample for sample in samples.values()
            ),
            "null_answer_count": sum(
                sample.get("answer") is None and "answer" in sample
                for sample in samples.values()
            ),
            "gold_document_count_distribution": dict(
                sorted(Counter(len(answer) for answer in gold_lists).items())
            ),
            "unique_gold_document_id_count": len(unique_gold_ids),
            "unique_gold_document_ids": sorted(unique_gold_ids),
            "duplicate_gold_ids_within_samples": duplicate_gold_ids,
        }
    )

    if corpus is not None:
        corpus_ids = {str(document.get("id")) for document in corpus if "id" in document}
        unresolved_ids = sorted(
            document_id
            for document_id in unique_gold_ids
            if str(document_id) not in corpus_ids
        )
        report["unresolved_gold_id_count"] = len(unresolved_ids)
        report["unresolved_gold_ids"] = unresolved_ids

    return report


def audit_legal_qa(samples: dict) -> dict:
    """Report LegalQA question and answer completeness and text lengths."""

    report = _question_audit(samples)
    answers = [
        sample["answer"]
        for sample in samples.values()
        if isinstance(sample.get("answer"), str)
    ]
    report.update(
        {
            "missing_answer_count": sum(
                "answer" not in sample for sample in samples.values()
            ),
            "null_answer_count": sum(
                sample.get("answer") is None and "answer" in sample
                for sample in samples.values()
            ),
            "empty_answer_count": sum(
                sample.get("answer") == "" for sample in samples.values()
            ),
            "answer_character_length": _length_statistics(answers),
        }
    )
    return report


def audit_corpus(documents: list[dict]) -> dict:
    """Report corpus identifiers, missing fields, and passage statistics."""

    document_ids = [document["id"] for document in documents if "id" in document]
    id_counts = Counter(document_ids)
    duplicate_ids = [
        {"document_id": document_id, "count": count}
        for document_id, count in id_counts.items()
        if count > 1
    ]

    passages = [
        document["passage"]
        for document in documents
        if isinstance(document.get("passage"), str)
    ]
    passage_groups = defaultdict(list)
    for document in documents:
        passage = document.get("passage")
        if isinstance(passage, str) and passage != "":
            passage_groups[passage].append(document.get("id"))

    duplicate_passages = [
        {
            "document_ids": ids,
            "count": len(ids),
            "character_length": len(passage),
        }
        for passage, ids in passage_groups.items()
        if len(ids) > 1
    ]

    return {
        "document_count": len(documents),
        "missing_document_id_count": sum("id" not in document for document in documents),
        "unique_document_id_count": len(id_counts),
        "duplicate_document_ids": duplicate_ids,
        "missing_passage_count": sum(
            "passage" not in document for document in documents
        ),
        "null_passage_count": sum(
            document.get("passage") is None and "passage" in document
            for document in documents
        ),
        "empty_passage_count": sum(
            document.get("passage") == "" for document in documents
        ),
        "missing_name_count": sum("name" not in document for document in documents),
        "null_name_count": sum(
            document.get("name") is None and "name" in document
            for document in documents
        ),
        "empty_name_count": sum(document.get("name") == "" for document in documents),
        "passage_character_length": _length_statistics(passages),
        "exact_duplicate_non_empty_passage_group_count": len(duplicate_passages),
        "exact_duplicate_non_empty_passage_groups": duplicate_passages,
    }


def audit_cross_task(legal_ir: dict, legal_qa: dict) -> dict:
    """Report exact overlaps; exact text does not prove a semantic pairing."""

    shared_sample_ids = sorted(set(legal_ir) & set(legal_qa))
    ir_questions = _question_groups(legal_ir)
    qa_questions = _question_groups(legal_qa)
    shared_questions = sorted(set(ir_questions) & set(qa_questions))

    cardinality_counts = {
        "one_to_one": 0,
        "one_to_many": 0,
        "many_to_one": 0,
        "many_to_many": 0,
    }
    question_groups = []
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
        question_groups.append(
            {
                "question": question,
                "cardinality": cardinality,
                "legal_ir_sample_ids": ir_ids,
                "legal_qa_sample_ids": qa_ids,
            }
        )

    return {
        "sample_id_overlap_count": len(shared_sample_ids),
        "sample_id_overlap": shared_sample_ids,
        "exact_question_text_overlap_count": len(shared_questions),
        "cardinality_counts": cardinality_counts,
        "question_groups": question_groups,
    }
