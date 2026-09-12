"""Simple lexical BM25 retrieval over fixed C0 chunks."""

import re
from time import perf_counter

import bm25s
import numpy as np


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
    return {
        "rankings": rankings,
        "top_k_chunks": top_k_chunks,
        "top_k_documents": top_k_documents,
        "retrieval_seconds": perf_counter() - started,
        "unique_documents_from_chunk_pool": {
            "min": int(counts.min()) if counts.size else None,
            "median": float(np.median(counts)) if counts.size else None,
            "p95": float(np.percentile(counts, 95)) if counts.size else None,
            "queries_below_200": int(np.sum(counts < 200)),
        },
    }
