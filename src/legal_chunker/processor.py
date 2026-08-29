import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from legal_chunker.context import get_context_for_position
from legal_chunker.extractors import build_packing_units
from legal_chunker.packers import pack_units
from legal_chunker.schemas import ChunkRecord, ChunkUnit
from legal_chunker.utils import unique_keep_order


def build_chunk_record(record: dict, chunk_units: list[ChunkUnit], chunk_index: int) -> ChunkRecord:
    document_id = record["document_id"]
    char_start = min(unit.char_start for unit in chunk_units)
    char_end = max(unit.char_end for unit in chunk_units)

    chunk_text = record["text"][char_start:char_end]
    context = get_context_for_position(record, char_start)

    articles = unique_keep_order([v for u in chunk_units for v in u.articles])
    clauses = unique_keep_order([v for u in chunk_units for v in u.clauses])
    points = unique_keep_order([v for u in chunk_units for v in u.points])

    chunk_id = f"{document_id}_chunk_{chunk_index:04d}"

    return ChunkRecord(
        document_id=document_id,
        chunk_id=chunk_id,
        chunk_index=chunk_index,
        document_title=record.get("document_title"),
        part_number=context["part_number"],
        part_title=context["part_title"],
        chapter_number=context["chapter_number"],
        chapter_title=context["chapter_title"],
        section_number=context["section_number"],
        section_title=context["section_title"],
        articles=articles,
        clauses=clauses,
        points=points,
        char_start=char_start,
        char_end=char_end,
        text=chunk_text,
    )


def chunk_document(record: dict) -> list[ChunkRecord]:
    units = build_packing_units(record)
    chunks_of_units = pack_units(units)

    return [
        build_chunk_record(
            record=record,
            chunk_units=chunk_units,
            chunk_index=i,
        )
        for i, chunk_units in enumerate(chunks_of_units)
    ]


def process_metadata_jsonl(
    input_path: str,
    output_jsonl: str,
    output_csv: str,
    output_stats: str,
):
    input_p = Path(input_path)
    all_chunks: list[ChunkRecord] = []

    total_documents = 0
    failed_documents = 0
    fallback_documents = 0

    with input_p.open("r", encoding="utf-8") as f:
        for line_idx, line in enumerate(f):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
                total_documents += 1

                fingerprint = record.get("fingerprint", [])
                if "article" not in fingerprint:
                    fallback_documents += 1

                chunks = chunk_document(record)
                all_chunks.extend(chunks)

            except Exception as e:
                failed_documents += 1
                print(f"[ERROR] line={line_idx}: {e}")

    out_jsonl = Path(output_jsonl)
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)

    with out_jsonl.open("w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")

    rows = [asdict(chunk) for chunk in all_chunks]
    df = pd.DataFrame(rows)

    if not df.empty:
        for col in ["articles", "clauses", "points"]:
            df[col] = df[col].apply(lambda x: json.dumps(x, ensure_ascii=False))

    df.to_csv(output_csv, index=False, encoding="utf-8-sig")

    if all_chunks:
        lengths = [len(c.text) for c in all_chunks]
        chunks_per_doc = {}
        for c in all_chunks:
            chunks_per_doc[c.document_id] = chunks_per_doc.get(c.document_id, 0) + 1

        stats = {
            "documents": total_documents,
            "failed_documents": failed_documents,
            "fallback_documents": fallback_documents,
            "chunks": len(all_chunks),
            "chunk_length": {
                "min": min(lengths),
                "max": max(lengths),
                "mean": sum(lengths) / len(lengths),
                "median": float(pd.Series(lengths).median()),
                "p95": float(pd.Series(lengths).quantile(0.95)),
            },
            "chunks_per_document": {
                "mean": sum(chunks_per_doc.values()) / len(chunks_per_doc),
                "median": float(pd.Series(list(chunks_per_doc.values())).median()),
                "max": max(chunks_per_doc.values()),
            },
        }
    else:
        stats = {
            "documents": total_documents,
            "failed_documents": failed_documents,
            "fallback_documents": fallback_documents,
            "chunks": 0,
        }

    with Path(output_stats).open("w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    print("STRUCTURE-AWARE CHUNKING COMPLETED")
    print("=" * 60)
    print(f"Documents : {total_documents:,}")
    print(f"Failed    : {failed_documents:,}")
    print(f"Fallback  : {fallback_documents:,}")
    print(f"Chunks    : {len(all_chunks):,}")