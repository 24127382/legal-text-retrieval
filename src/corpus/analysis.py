"""Read-only diagnostics for exploring the raw legal corpus structure.

The regular expressions in this module detect candidate markers only. They are
deliberately conservative and are not a legal-document parser.
"""

import re
from collections import Counter

import numpy as np


PART_PATTERN = re.compile(r"^\s*PHẦN\s+(?:THỨ\s+\w+|[IVXLCDM]+|\d+)\b", re.IGNORECASE)
CHAPTER_PATTERN = re.compile(r"^\s*CHƯƠNG\s+(?:[IVXLCDM]+|\d+)\b", re.IGNORECASE)
SECTION_PATTERN = re.compile(r"^\s*MỤC\s+(?:[IVXLCDM]+|\d+[A-ZĐ]?)\b", re.IGNORECASE)
ARTICLE_PATTERN = re.compile(r"^\s*ĐIỀU\s+\d+[A-ZĐ]?\b", re.IGNORECASE)
NUMBERED_CLAUSE_PATTERN = re.compile(r"^\s*\d+[.)]\s+(?=\S)")
LETTERED_POINT_PATTERN = re.compile(r"^\s*[a-zđ][.)]\s+(?=\S)")

_CANDIDATE_PATTERNS = {
    "part": PART_PATTERN,
    "chapter": CHAPTER_PATTERN,
    "section": SECTION_PATTERN,
    "article": ARTICLE_PATTERN,
    "numbered_clause": NUMBERED_CLAUSE_PATTERN,
    "lettered_point": LETTERED_POINT_PATTERN,
}
_EXAMPLE_LIMIT = 10
_OUTLIER_LIMIT = 5
_EXAMPLE_CHARACTER_LIMIT = 200
_ARTICLE_LENGTH_THRESHOLDS = (2_000, 5_000, 10_000, 20_000)
_NO_ARTICLE_LENGTH_THRESHOLDS = (1_000, 5_000, 10_000)


def _distribution(values: list[int]) -> dict:
    if not values:
        return {"min": None, "median": None, "mean": None, "p95": None, "max": None}

    array = np.asarray(values)
    return {
        "min": int(array.min()),
        "median": float(np.median(array)),
        "mean": round(float(array.mean()), 2),
        "p95": round(float(np.percentile(array, 95)), 2),
        "max": int(array.max()),
    }


def _example_line(line: str) -> str:
    line = line.strip()
    if len(line) <= _EXAMPLE_CHARACTER_LIMIT:
        return line
    return f"{line[:_EXAMPLE_CHARACTER_LIMIT - 1]}…"


def _format_variant_key(name: str, line: str, match: re.Match) -> tuple:
    marker = match.group(0).strip()
    remainder = line[match.end() :]
    separator = "end"
    if remainder:
        separator = "space" if remainder[0].isspace() else remainder[0]

    if name in {"part", "chapter", "section", "article"}:
        label, _, identifier = marker.partition(" ")
        if identifier.isdigit():
            numbering = "digit"
        elif identifier and all(
            character in "IVXLCDM" for character in identifier.upper()
        ):
            numbering = "roman"
        else:
            numbering = "other"
        return label, numbering, separator

    if name == "lettered_point":
        return marker[0], marker[-1]
    return (marker[-1],)


def _document_summary(record: dict) -> dict:
    return {
        "document_id": record["document_id"],
        "character_length": record["character_length"],
        "line_count": record["line_count"],
        "blank_line_count": record["blank_line_count"],
        "candidate_article_count": record["marker_counts"]["article"],
    }


def _candidate_article_segments(
    document_id, passage: str, candidates: list[tuple[int, str]]
) -> list[dict]:
    segments = []
    for index, (start, heading) in enumerate(candidates):
        end = candidates[index + 1][0] if index + 1 < len(candidates) else len(passage)
        segments.append(
            {
                "document_id": document_id,
                "article_index": index + 1,
                "candidate_heading": heading,
                "character_length": end - start,
            }
        )
    return segments


def analyze_corpus(documents: list[dict]) -> dict:
    """Return compact, JSON-serializable diagnostics for raw corpus documents.

    Passage strings are inspected without modifying the documents or their text.
    Marker counts are line-based candidates, not parsed legal structure.
    """

    records = []
    fallback_examples = {name: [] for name in _CANDIDATE_PATTERNS}
    seen_examples = {name: set() for name in _CANDIDATE_PATTERNS}
    variant_examples = {name: {} for name in _CANDIDATE_PATTERNS}

    for document in documents:
        passage = document.get("passage")
        if not isinstance(passage, str):
            raise TypeError(
                f"document {document.get('id')!r}: passage must be a string"
            )

        lines = passage.splitlines()
        lines_with_endings = passage.splitlines(keepends=True)
        marker_counts = {name: 0 for name in _CANDIDATE_PATTERNS}
        article_candidates = []
        line_start = 0
        for line, line_with_ending in zip(lines, lines_with_endings):
            for name, pattern in _CANDIDATE_PATTERNS.items():
                match = pattern.match(line)
                if not match:
                    continue

                marker_counts[name] += 1
                example = _example_line(line)
                if name == "article":
                    article_candidates.append((line_start, example))
                if (
                    len(fallback_examples[name]) < _EXAMPLE_LIMIT
                    and example not in seen_examples[name]
                ):
                    fallback_examples[name].append(example)
                    seen_examples[name].add(example)
                variant_key = _format_variant_key(name, line, match)
                variant_examples[name].setdefault(variant_key, example)
            line_start += len(line_with_ending)

        article_segments = _candidate_article_segments(
            document.get("id"), passage, article_candidates
        )

        records.append(
            {
                "document_id": document.get("id"),
                "character_length": len(passage),
                "line_count": len(lines),
                "blank_line_count": sum(not line.strip() for line in lines),
                "marker_counts": marker_counts,
                "is_empty": passage == "",
                "candidate_article_segments": article_segments,
                "prefix_character_length": (
                    article_candidates[0][0] if article_candidates else None
                ),
            }
        )

    character_lengths = [record["character_length"] for record in records]
    line_counts = [record["line_count"] for record in records]
    blank_line_counts = [record["blank_line_count"] for record in records]
    article_counts = [record["marker_counts"]["article"] for record in records]
    non_empty_records = [record for record in records if not record["is_empty"]]
    records_with_articles = [
        record for record in records if record["candidate_article_segments"]
    ]
    records_without_articles = [
        record for record in records if not record["candidate_article_segments"]
    ]
    candidate_article_segments = [
        segment
        for record in records_with_articles
        for segment in record["candidate_article_segments"]
    ]
    article_segment_lengths = [
        segment["character_length"] for segment in candidate_article_segments
    ]
    prefix_lengths = [
        record["prefix_character_length"] for record in records_with_articles
    ]

    marker_coverage = {}
    for name in _CANDIDATE_PATTERNS:
        counts = [record["marker_counts"][name] for record in records]
        marker_coverage[name] = {
            "document_count": sum(count > 0 for count in counts),
            "document_fraction": round(
                sum(count > 0 for count in counts) / len(records), 6
            )
            if records
            else 0.0,
            "total_candidate_marker_count": sum(counts),
        }

    total_line_count = sum(line_counts)
    single_line_count = sum(record["line_count"] <= 1 for record in non_empty_records)

    longest = sorted(
        records, key=lambda record: record["character_length"], reverse=True
    )[:_OUTLIER_LIMIT]
    shortest_non_empty = sorted(
        non_empty_records, key=lambda record: record["character_length"]
    )[:_OUTLIER_LIMIT]
    without_articles = sorted(
        (record for record in records if record["marker_counts"]["article"] == 0),
        key=lambda record: record["character_length"],
        reverse=True,
    )[:_OUTLIER_LIMIT]
    most_articles = sorted(
        records,
        key=lambda record: record["marker_counts"]["article"],
        reverse=True,
    )[:_OUTLIER_LIMIT]
    most_lines = sorted(
        records, key=lambda record: record["line_count"], reverse=True
    )[:_OUTLIER_LIMIT]
    all_empty_passages = [record for record in records if record["is_empty"]]
    empty_passages = all_empty_passages[:_OUTLIER_LIMIT]

    marker_examples = {}
    for name in _CANDIDATE_PATTERNS:
        examples = list(variant_examples[name].values())[:_EXAMPLE_LIMIT]
        for example in fallback_examples[name]:
            if len(examples) == _EXAMPLE_LIMIT:
                break
            if example not in examples:
                examples.append(example)
        marker_examples[name] = examples

    article_length_thresholds = {}
    for threshold in _ARTICLE_LENGTH_THRESHOLDS:
        count = sum(length > threshold for length in article_segment_lengths)
        article_length_thresholds[f"greater_than_{threshold}_characters"] = {
            "count": count,
            "fraction": (
                round(count / len(article_segment_lengths), 6)
                if article_segment_lengths
                else 0.0
            ),
        }

    no_article_length_thresholds = {}
    for threshold in _NO_ARTICLE_LENGTH_THRESHOLDS:
        count = sum(
            record["character_length"] < threshold
            for record in records_without_articles
        )
        no_article_length_thresholds[f"under_{threshold}_characters"] = {
            "count": count,
            "fraction": (
                round(count / len(records_without_articles), 6)
                if records_without_articles
                else 0.0
            ),
        }

    longest_article_segments = sorted(
        candidate_article_segments,
        key=lambda segment: segment["character_length"],
        reverse=True,
    )[:_OUTLIER_LIMIT]
    shortest_article_segments = sorted(
        candidate_article_segments,
        key=lambda segment: segment["character_length"],
    )[:_OUTLIER_LIMIT]
    longest_prefixes = sorted(
        records_with_articles,
        key=lambda record: record["prefix_character_length"],
        reverse=True,
    )[:_OUTLIER_LIMIT]

    return {
        "document_count": len(documents),
        "document_size": {
            "character_length": _distribution(character_lengths),
            "line_count": _distribution(line_counts),
        },
        "legal_structure_coverage": {
            "candidate_markers": marker_coverage,
            "candidate_article_count_per_document": _distribution(article_counts),
            "candidate_article_count_distribution": dict(
                sorted(Counter(article_counts).items())
            ),
            "documents_without_candidate_article_count": sum(
                count == 0 for count in article_counts
            ),
            "documents_without_candidate_article_fraction": round(
                sum(count == 0 for count in article_counts) / len(records), 6
            )
            if records
            else 0.0,
        },
        "candidate_article_segments": {
            "total_segment_count": len(candidate_article_segments),
            "document_count": len(records_with_articles),
            "document_fraction": (
                round(len(records_with_articles) / len(records), 6)
                if records
                else 0.0
            ),
            "segment_count_per_document": _distribution(
                [
                    len(record["candidate_article_segments"])
                    for record in records_with_articles
                ]
            ),
            "character_length": _distribution(article_segment_lengths),
            "character_length_thresholds": article_length_thresholds,
            "prefix_character_length": {
                "distribution": _distribution(prefix_lengths),
                "empty_count": sum(length == 0 for length in prefix_lengths),
                "non_empty_count": sum(length > 0 for length in prefix_lengths),
            },
            "outliers": {
                "longest_segments": longest_article_segments,
                "shortest_segments": shortest_article_segments,
                "documents_with_most_segments": [
                    _document_summary(record) for record in most_articles
                ],
                "longest_prefixes": [
                    {
                        "document_id": record["document_id"],
                        "candidate_heading": record["candidate_article_segments"][0][
                            "candidate_heading"
                        ],
                        "character_length": record["prefix_character_length"],
                    }
                    for record in longest_prefixes
                ],
            },
        },
        "documents_without_candidate_articles": {
            "document_count": len(records_without_articles),
            "document_fraction": (
                round(len(records_without_articles) / len(records), 6)
                if records
                else 0.0
            ),
            "character_length": _distribution(
                [record["character_length"] for record in records_without_articles]
            ),
            "line_count": _distribution(
                [record["line_count"] for record in records_without_articles]
            ),
            "character_length_thresholds": no_article_length_thresholds,
            "longest_documents": [
                _document_summary(record) for record in without_articles
            ],
        },
        "formatting_examples": {
            f"{name}_examples": examples
            for name, examples in marker_examples.items()
        },
        "line_structure": {
            "total_line_count": total_line_count,
            "total_blank_line_count": sum(blank_line_counts),
            "blank_line_fraction": (
                round(sum(blank_line_counts) / total_line_count, 6)
                if total_line_count
                else 0.0
            ),
            "documents_with_blank_lines_count": sum(
                count > 0 for count in blank_line_counts
            ),
            "non_empty_documents_with_at_most_one_line_count": single_line_count,
            "non_empty_documents_with_at_most_one_line_fraction": (
                round(single_line_count / len(non_empty_records), 6)
                if non_empty_records
                else 0.0
            ),
            "empty_passage_count": len(all_empty_passages),
        },
        "outliers": {
            "longest_documents": [_document_summary(record) for record in longest],
            "shortest_non_empty_documents": [
                _document_summary(record) for record in shortest_non_empty
            ],
            "longest_documents_without_candidate_articles": [
                _document_summary(record) for record in without_articles
            ],
            "documents_with_most_candidate_articles": [
                _document_summary(record) for record in most_articles
            ],
            "documents_with_most_lines": [
                _document_summary(record) for record in most_lines
            ],
            "empty_passages": [
                _document_summary(record) for record in empty_passages
            ],
        },
    }
