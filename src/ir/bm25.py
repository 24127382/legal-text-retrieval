"""Simple lexical BM25 retrieval over fixed-window chunks."""

import re
from time import perf_counter

import bm25s
import numpy as np

from .aggregate import AGGREGATION_METHODS, aggregate_documents

TOKEN_PATTERN = re.compile(r"\w+", flags=re.UNICODE)


def lexical_tokenize(text: str) -> list[str]:
    """Lowercase and split text into Unicode letter/digit/underscore tokens."""

    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return TOKEN_PATTERN.findall(text.lower())


def _sparse_index_size_bytes(retriever: bm25s.BM25) -> int:
    return sum(
        value.nbytes
        for value in retriever.scores.values()
        if isinstance(value, np.ndarray)
    )


def build_bm25(
    chunks: list[dict], k1: float = 1.5, b: float = 0.75
) -> dict:
    """Build a bm25s Lucene-style sparse index and retain compact chunk metadata."""

    if not chunks:
        raise ValueError("chunks must not be empty")

    started = perf_counter()
    tokenized_chunks = bm25s.tokenize(
        [chunk["text"] for chunk in chunks],
        lower=True,
        token_pattern=r"(?u)\w+",
        stopwords=[],
        stemmer=None,
        return_ids=True,
        show_progress=False,
    )
    retriever = bm25s.BM25(k1=k1, b=b, method="lucene")
    retriever.index(tokenized_chunks, show_progress=False)

    return {
        "retriever": retriever,
        "chunk_metadata": [
            (str(chunk["chunk_id"]), str(chunk["document_id"])) for chunk in chunks
        ],
        "number_of_chunks": len(chunks),
        "k1": k1,
        "b": b,
        "method": "lucene",
        "library": "bm25s",
        "library_version": bm25s.__version__,
        "build_seconds": perf_counter() - started,
        "sparse_index_size_bytes": _sparse_index_size_bytes(retriever),
    }


def retrieve_bm25(
    index: dict,
    samples: dict,
    top_k_chunks: int = 1_000,
    top_k_documents: int = 200,
    batch_size: int = 64,
    candidate_depths: tuple[int, ...] = (10, 20, 50, 100, 200),
) -> dict:
    """Retrieve chunks in batches and aggregate unique documents by max score.

    Because chunk hits are sorted by descending BM25 score, the first occurrence
    of a document is its highest-scoring supporting chunk. Only document rankings
    are retained; the full chunk-hit pools are discarded after each batch.
    """

    if top_k_chunks <= 0:
        raise ValueError("top_k_chunks must be greater than zero")
    if top_k_documents <= 0:
        raise ValueError("top_k_documents must be greater than zero")
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")
    if any(depth <= 0 for depth in candidate_depths):
        raise ValueError("candidate_depths must contain only positive integers")
    if top_k_chunks > index["number_of_chunks"]:
        raise ValueError("top_k_chunks cannot exceed the number of indexed chunks")

    sample_items = list(samples.items())
    rankings = {}
    unique_document_counts = []
    started = perf_counter()

    for batch_start in range(0, len(sample_items), batch_size):
        batch = sample_items[batch_start : batch_start + batch_size]
        query_tokens = []
        for sample_id, sample in batch:
            question = sample.get("question")
            if not isinstance(question, str):
                raise TypeError(f"sample {sample_id!r}: question must be a string")
            query_tokens.append(lexical_tokenize(question))

        chunk_indices = index["retriever"].retrieve(
            query_tokens,
            k=top_k_chunks,
            sorted=True,
            return_as="documents",
            show_progress=False,
        )

        for (sample_id, _), hit_indices in zip(batch, chunk_indices):
            seen_documents = set()
            ranked_documents = []
            for chunk_index in hit_indices:
                document_id = index["chunk_metadata"][int(chunk_index)][1]
                if document_id in seen_documents:
                    continue
                seen_documents.add(document_id)
                if len(ranked_documents) < top_k_documents:
                    ranked_documents.append(document_id)

            rankings[str(sample_id)] = ranked_documents
            unique_document_counts.append(len(seen_documents))

    counts = np.asarray(unique_document_counts, dtype=np.int32)
    requested_depths = tuple(dict.fromkeys(candidate_depths))
    return {
        "rankings": rankings,
        "top_k_chunks": top_k_chunks,
        "top_k_documents": top_k_documents,
        "retrieval_seconds": perf_counter() - started,
        "unique_documents_from_chunk_pool": {
            "min": int(counts.min()) if counts.size else None,
            "median": float(np.median(counts)) if counts.size else None,
            "p95": float(np.percentile(counts, 95)) if counts.size else None,
            "queries_below_depth": {
                depth: int(np.sum(counts < depth)) for depth in requested_depths
            },
        },
    }


def retrieve_bm25_aggregations(
    index: dict,
    samples: dict,
    methods: tuple[str, ...] = AGGREGATION_METHODS,
    top_k_chunks: int = 2_000,
    batch_size: int = 64,
    candidate_depths: tuple[int, ...] = (10, 20, 50, 100, 200),
) -> dict:
    """Retrieve one shared chunk-hit pool and rank it with each aggregation.

    Full document rankings are retained so candidate-pool recall and first-gold
    ranks can be measured without treating rank 200 as a retrieval miss. The
    chunk-hit records are discarded after each query is aggregated.
    """

    if top_k_chunks <= 0:
        raise ValueError("top_k_chunks must be greater than zero")
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")
    if any(depth <= 0 for depth in candidate_depths):
        raise ValueError("candidate_depths must contain only positive integers")
    if top_k_chunks > index["number_of_chunks"]:
        raise ValueError("top_k_chunks cannot exceed the number of indexed chunks")

    requested_methods = tuple(dict.fromkeys(methods))
    if not requested_methods:
        raise ValueError("methods must not be empty")
    unknown_methods = [
        method for method in requested_methods if method not in AGGREGATION_METHODS
    ]
    if unknown_methods:
        raise ValueError(f"unknown aggregation methods: {unknown_methods}")

    sample_items = list(samples.items())
    rankings_by_method = {method: {} for method in requested_methods}
    unique_document_counts = []
    supporting_chunk_counts = []
    started = perf_counter()

    for batch_start in range(0, len(sample_items), batch_size):
        batch = sample_items[batch_start : batch_start + batch_size]
        query_tokens = []
        for sample_id, sample in batch:
            question = sample.get("question")
            if not isinstance(question, str):
                raise TypeError(f"sample {sample_id!r}: question must be a string")
            query_tokens.append(lexical_tokenize(question))

        retrieval_result = index["retriever"].retrieve(
            query_tokens,
            k=top_k_chunks,
            sorted=True,
            return_as="tuple",
            show_progress=False,
        )

        for (sample_id, _), hit_indices, hit_scores in zip(
            batch, retrieval_result.documents, retrieval_result.scores
        ):
            chunk_hits = []
            for chunk_rank, (chunk_index, score) in enumerate(
                zip(hit_indices, hit_scores), start=1
            ):
                chunk_id, document_id = index["chunk_metadata"][int(chunk_index)]
                chunk_hits.append(
                    {
                        "chunk_id": chunk_id,
                        "document_id": document_id,
                        "score": float(score),
                        "chunk_rank": chunk_rank,
                    }
                )

            expected_candidate_ids = {hit["document_id"] for hit in chunk_hits}
            for method in requested_methods:
                aggregated = aggregate_documents(chunk_hits, method=method)
                ranked_document_ids = [
                    document["document_id"] for document in aggregated
                ]
                if set(ranked_document_ids) != expected_candidate_ids:
                    raise RuntimeError(
                        f"sample {sample_id!r}: aggregation changed candidate universe"
                    )
                rankings_by_method[method][str(sample_id)] = ranked_document_ids

                if method == requested_methods[0]:
                    supporting_chunk_counts.extend(
                        document["supporting_chunk_count"] for document in aggregated
                    )

            unique_document_counts.append(len(expected_candidate_ids))

    counts = np.asarray(unique_document_counts, dtype=np.int32)
    support_counts = np.asarray(supporting_chunk_counts, dtype=np.int32)
    requested_depths = tuple(dict.fromkeys(candidate_depths))
    return {
        "rankings_by_method": rankings_by_method,
        "methods": requested_methods,
        "top_k_chunks": top_k_chunks,
        "retrieval_seconds": perf_counter() - started,
        "candidate_universe_check": {
            "consistent_across_methods": True,
            "queries_checked": len(sample_items),
        },
        "unique_documents_from_chunk_pool": {
            "min": int(counts.min()) if counts.size else None,
            "median": float(np.median(counts)) if counts.size else None,
            "p95": float(np.percentile(counts, 95)) if counts.size else None,
            "queries_below_depth": {
                depth: int(np.sum(counts < depth)) for depth in requested_depths
            },
        },
        "retrieved_chunks_per_candidate_document": {
            "median": float(np.median(support_counts)) if support_counts.size else None,
            "p95": (
                float(np.percentile(support_counts, 95))
                if support_counts.size
                else None
            ),
            "max": int(support_counts.max()) if support_counts.size else None,
        },
    }
