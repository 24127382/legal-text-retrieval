"""Chunk-to-document score aggregation for lexical retrieval."""

from math import isfinite

AGGREGATION_METHODS = ("max", "mean_top_2", "mean_top_3", "sum_top_2")


def aggregate_documents(chunk_hits: list[dict], method: str = "max") -> list[dict]:
    """Aggregate one query's chunk hits into a deterministic document ranking.

    Ties use the best (lowest) supporting chunk rank, then the canonical string
    document ID. Every unique document in ``chunk_hits`` appears exactly once.
    """

    if method not in AGGREGATION_METHODS:
        raise ValueError(
            f"unknown aggregation method {method!r}; expected one of "
            f"{AGGREGATION_METHODS}"
        )

    grouped: dict[str, dict] = {}
    for hit in chunk_hits:
        document_id = str(hit["document_id"])
        chunk_rank = hit["chunk_rank"]
        if not isinstance(chunk_rank, int) or isinstance(chunk_rank, bool):
            raise TypeError("chunk_rank must be an integer")
        if chunk_rank <= 0:
            raise ValueError("chunk_rank must be greater than zero")

        score = float(hit["score"])
        if not isfinite(score):
            raise ValueError("chunk score must be finite")

        document = grouped.setdefault(
            document_id,
            {"scores": [], "best_chunk_rank": chunk_rank},
        )
        document["scores"].append(score)
        document["best_chunk_rank"] = min(document["best_chunk_rank"], chunk_rank)

    ranked_documents = []
    for document_id, document in grouped.items():
        scores = sorted(document["scores"], reverse=True)
        if method == "max":
            aggregate_score = scores[0]
        elif method == "mean_top_2":
            selected_scores = scores[:2]
            aggregate_score = sum(selected_scores) / len(selected_scores)
        elif method == "mean_top_3":
            selected_scores = scores[:3]
            aggregate_score = sum(selected_scores) / len(selected_scores)
        else:
            aggregate_score = sum(scores[:2])

        ranked_documents.append(
            {
                "document_id": document_id,
                "score": aggregate_score,
                "best_chunk_rank": document["best_chunk_rank"],
                "supporting_chunk_count": len(scores),
            }
        )

    ranked_documents.sort(
        key=lambda document: (
            -document["score"],
            document["best_chunk_rank"],
            document["document_id"],
        )
    )
    return ranked_documents
