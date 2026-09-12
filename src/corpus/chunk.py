"""Deterministic fixed-size character windows for corpus baseline C0."""

from collections import Counter


def _validate_window_parameters(chunk_size: int, overlap: int) -> None:
    if not isinstance(chunk_size, int) or isinstance(chunk_size, bool):
        raise TypeError("chunk_size must be an integer")
    if not isinstance(overlap, int) or isinstance(overlap, bool):
        raise TypeError("overlap must be an integer")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if overlap < 0:
        raise ValueError("overlap must be non-negative")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")


def chunk_document(
    document: dict, chunk_size: int = 2_000, overlap: int = 200
) -> list[dict]:
    """Split one document into source-preserving character windows.

    Empty passages produce no chunks. Every chunk's half-open offsets refer
    directly to the unmodified ``document["passage"]`` string.
    """

    _validate_window_parameters(chunk_size, overlap)

    document_id = str(document["id"])
    text = document["passage"]
    if not isinstance(text, str):
        raise TypeError(f"document {document_id!r}: passage must be a string")
    if not text:
        return []

    step = chunk_size - overlap
    chunks = []
    for chunk_index, char_start in enumerate(range(0, len(text), step)):
        char_end = min(char_start + chunk_size, len(text))
        chunks.append(
            {
                "chunk_id": f"{document_id}:{chunk_index}",
                "document_id": document_id,
                "chunk_index": chunk_index,
                "text": text[char_start:char_end],
                "char_start": char_start,
                "char_end": char_end,
            }
        )
        if char_end == len(text):
            break

    return chunks


def chunk_corpus(
    documents: list[dict], chunk_size: int = 2_000, overlap: int = 200
) -> list[dict]:
    """Return C0 fixed-window chunks for corpus documents in input order."""

    _validate_window_parameters(chunk_size, overlap)

    chunks = []
    seen_document_ids = set()
    for document in documents:
        document_id = str(document["id"])
        if document_id in seen_document_ids:
            raise ValueError(
                f"duplicate document ID after canonicalization: {document_id}"
            )
        seen_document_ids.add(document_id)
        chunks.extend(chunk_document(document, chunk_size=chunk_size, overlap=overlap))
    return chunks


def _distribution(values: list[int]) -> dict:
    if not values:
        return {"median": None, "p95": None, "max": None}

    ordered = sorted(values)

    def percentile(percent: int) -> float:
        position = (len(ordered) - 1) * percent / 100
        lower = int(position)
        upper = min(lower + 1, len(ordered) - 1)
        fraction = position - lower
        return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction

    return {
        "median": float(percentile(50)),
        "p95": round(float(percentile(95)), 2),
        "max": max(ordered),
    }


def analyze_chunks(documents: list[dict], chunks: list[dict]) -> dict:
    """Return compact C0 chunk counts and character-length statistics."""

    chunk_counts = Counter(chunk["document_id"] for chunk in chunks)
    document_ids = [str(document["id"]) for document in documents]
    chunk_ids = Counter(chunk["chunk_id"] for chunk in chunks)

    return {
        "total_chunks": len(chunks),
        "chunks_per_document": _distribution(
            [chunk_counts[document_id] for document_id in document_ids]
        ),
        "chunk_character_length": _distribution(
            [len(chunk["text"]) for chunk in chunks]
        ),
        "documents_with_zero_chunks": sum(
            chunk_counts[document_id] == 0 for document_id in document_ids
        ),
        "duplicate_chunk_ids": sum(count - 1 for count in chunk_ids.values()),
    }
