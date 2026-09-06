from __future__ import annotations

import json
import logging
import os
import pickle
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional

import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

from src.chunker import chunk_document
from src.parser import load_raw_documents, parse_document

from src.bm25 import BM25
DEFAULT_CHUNKING_CONFIG: Dict[str, Any] = {
    "target_size": 5000,
    "soft_limit": 5000,
    "hard_limit": 6000,
    "progress_interval": 100,
}


def run_parsing_stage(
    data_dir: str,
    output_csv: str,
    output_jsonl: str,
    logger: Optional[logging.Logger] = None,
) -> str:
    """Giai đoạn 1: Đọc thư mục JSON thô -> Làm sạch -> Trích xuất cấu trúc -> Xuất metadata.jsonl"""
    log = logger or logging.getLogger(__name__)
    log.info("--- GIAI ĐOẠN 1: Đọc và trích xuất cấu trúc từ %s ---", data_dir)

    cleaned_docs = load_raw_documents(data_dir)
    if not cleaned_docs:
        raise ValueError(f"Không tìm thấy dữ liệu hợp lệ trong thư mục: {data_dir}")

    csv_path = Path(output_csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(cleaned_docs)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    log.info("✔ Đã lưu file text sạch: %s (%d văn bản)", csv_path, len(df))

    jsonl_path = Path(output_jsonl)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    total, failed = 0, 0
    with jsonl_path.open("w", encoding="utf-8") as f:
        for idx, row in df.iterrows():
            try:
                doc_id = str(row["document_id"])
                text = str(row["cleaned_text"]) if pd.notna(row["cleaned_text"]) else ""
                title = str(row["document_title"]).strip() if pd.notna(row["document_title"]) else None
                link = str(row["link"]).strip() if "link" in row and pd.notna(row["link"]) else None

                metadata = parse_document(
                    document_id=doc_id,
                    text=text,
                    document_title=title,
                    document_link=link,
                )
                f.write(json.dumps(asdict(metadata), ensure_ascii=False) + "\n")
                total += 1
            except Exception as e:
                failed += 1
                log.error("[ERROR] Dòng %s (ID: %s): %s", idx, row.get("document_id"), e)

    log.info("✔ Đã hoàn tất parse metadata: %d thành công, %d thất bại", total, failed)
    return str(jsonl_path)


def process_metadata_jsonl(
    input_path: str,
    output_jsonl: str,
    output_csv: str,
    output_stats: str,
    target_size: int = 5000,
    soft_limit: int = 5000,
    hard_limit: int = 6000,
    *,
    logger: Optional[logging.Logger] = None,
    progress_interval: int = 100,
) -> Dict[str, Any]:
    """Giai đoạn 2: Chia chunk từ metadata.jsonl -> Xuất chunks.jsonl, chunks.csv, stats.json"""
    logger = logger or logging.getLogger(__name__)
    logger.info("--- GIAI ĐOẠN 2: Tiến hành chunking từ file metadata ---")

    all_chunks = []
    total = failed = fallback = 0

    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Không tìm thấy file metadata: {input_file}")

    with input_file.open("r", encoding="utf-8") as f:
        for line_idx, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                total += 1
                if "article" not in record.get("fingerprint", []):
                    fallback += 1

                chunks = chunk_document(record, target_size, soft_limit, hard_limit)
                all_chunks.extend(chunks)

                if progress_interval and total % progress_interval == 0:
                    logger.info("Đã xử lý %d văn bản -> %d chunks", total, len(all_chunks))
            except Exception as exc:
                failed += 1
                logger.error("[ERROR] Dòng %d: %s", line_idx, exc)

    oj, oc, os_path = map(Path, (output_jsonl, output_csv, output_stats))
    for p in (oj, oc, os_path):
        p.parent.mkdir(parents=True, exist_ok=True)

    with oj.open("w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")

    df = pd.DataFrame([asdict(c) for c in all_chunks])
    if not df.empty:
        for col in ("articles", "clauses", "points"):
            df[col] = df[col].map(lambda x: json.dumps(x, ensure_ascii=False))
        df.to_csv(oc, index=False, encoding="utf-8-sig")

    lengths = [c.char_length for c in all_chunks]
    s = pd.Series(lengths) if lengths else pd.Series(dtype=float)
    counts = pd.Series([c.document_id for c in all_chunks]).value_counts() if all_chunks else pd.Series(dtype=float)

    stats = {
        "documents": total,
        "failed_documents": failed,
        "fallback_documents": fallback,
        "chunks": len(all_chunks),
    }

    if lengths:
        stats["chunk_length"] = {
            "min": int(s.min()),
            "max": int(s.max()),
            "mean": float(s.mean()),
            "median": float(s.median()),
            "p90": float(s.quantile(0.9)),
            "p95": float(s.quantile(0.95)),
            "p99": float(s.quantile(0.99)),
        }
        stats["length_buckets"] = {
            "<1000": int((s < 1000).sum()),
            "1000-3000": int(((s >= 1000) & (s < 3000)).sum()),
            "3000-5000": int(((s >= 3000) & (s < 5000)).sum()),
            "5000-5500": int(((s >= 5000) & (s < 5500)).sum()),
            "5500-6000": int(((s >= 5500) & (s <= 6000)).sum()),
            ">6000": int((s > 6000).sum()),
        }
        stats["chunks_per_document"] = {
            "mean": float(counts.mean()),
            "median": float(counts.median()),
            "max": int(counts.max()),
        }

    with os_path.open("w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    logger.info("==========================================")
    logger.info("TỔNG KẾT QUÁ TRÌNH CHUNKING")
    logger.info("==========================================")
    logger.info("Tổng văn bản xử lý : %d", total)
    logger.info("Tổng số chunks     : %d", len(all_chunks))
    logger.info("==========================================")

    return stats


def run_indexing_stage(
    chunks_jsonl: str,
    output_index_path: str,
    output_id_mapping_path: str,
    model_name: str = "BAAI/bge-m3",
    batch_size: int = 32,
    checkpoint_size: int = 15000,
    logger: Optional[logging.Logger] = None,
    output_bm25_path: Optional[str] = None,
) -> None:
    """Build the FAISS and BM25 indexes for the chunks file."""
    log = logger or logging.getLogger(__name__)
    log.info("--- GIAI ĐOẠN 3: Đang tính toán Embeddings & Tạo FAISS Index ---")

    input_file = Path(chunks_jsonl)
    if not input_file.exists():
        raise FileNotFoundError(f"Không tìm thấy file chunks: {input_file}")

    chunks = []
    with input_file.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))

    index_path = Path(output_index_path)
    id_map_path = Path(output_id_mapping_path)
    
    start_idx = 0
    existing_ids = []
    
    if index_path.exists() and id_map_path.exists():
        log.info(f"Phát hiện Checkpoint cũ. Đang tải {index_path}...")
        index = faiss.read_index(str(index_path))
        with id_map_path.open("r", encoding="utf-8") as f:
            existing_ids = json.load(f)
        start_idx = len(existing_ids)
        log.info(f"Đã tải {start_idx} vectors. Bỏ qua các chunks đã xử lý.")
    else:
        index = None

    if start_idx < len(chunks):
        remaining_chunks = chunks[start_idx:]
        log.info("Khởi tạo mô hình Embedding: %s", model_name)
        model = SentenceTransformer(model_name)

        for block_start in range(0, len(remaining_chunks), checkpoint_size):
            block_chunks = remaining_chunks[block_start : block_start + checkpoint_size]
            texts = [c["text"] for c in block_chunks]
            chunk_ids = [c["chunk_id"] for c in block_chunks]

            current_step = start_idx + block_start
            log.info(
                "Đang xử lý block %d đến %d / %d...",
                current_step,
                current_step + len(block_chunks),
                len(chunks),
            )

            embeddings = model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=True,
                normalize_embeddings=True,
            )
            embeddings = np.array(embeddings, dtype=np.float32)

            if index is None:
                index = faiss.IndexFlatIP(embeddings.shape[1])

            index.add(embeddings)
            existing_ids.extend(chunk_ids)

            index_path.parent.mkdir(parents=True, exist_ok=True)
            faiss.write_index(index, str(index_path))
            with id_map_path.open("w", encoding="utf-8") as f:
                json.dump(existing_ids, f, ensure_ascii=False, indent=2)

            log.info("✔ Đã lưu Checkpoint an toàn: %d vectors.", index.ntotal)
    else:
        log.info("FAISS đã có đủ %d vectors; bỏ qua bước embedding.", len(chunks))

    bm25_path = Path(output_bm25_path) if output_bm25_path else index_path.with_name("bm25.pkl")
    bm25_path.parent.mkdir(parents=True, exist_ok=True)
    bm25_index = BM25.create_index([chunk["text"] for chunk in chunks])
    with bm25_path.open("wb") as f:
        pickle.dump(
            {
                "index": bm25_index,
                "chunk_ids": [chunk["chunk_id"] for chunk in chunks],
            },
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    log.info("✔ Đã lưu BM25 index: %s (%d chunks).", bm25_path, len(chunks))

    log.info("✔ HOÀN TẤT TOÀN BỘ QUÁ TRÌNH INDEXING!")


def run_full_pipeline(
    input_dir: str,
    output_dir: str,
    config: Optional[Dict[str, Any]] = None,
    run_embedding: bool = False,
    model_name: str = "BAAI/bge-m3",
    logger: Optional[logging.Logger] = None,
) -> Dict[str, Any]:
    """Hàm chạy toàn bộ pipeline end-to-end (Parse -> Chunk -> FAISS Index)"""
    logger = logger or logging.getLogger(__name__)
    cfg = dict(DEFAULT_CHUNKING_CONFIG)
    if config:
        cfg.update(config)

    output_path = Path(output_dir)
    metadata_jsonl = output_path / "metadata.jsonl"
    cleaned_csv = output_path / "cleaned_data.csv"
    chunks_jsonl = output_path / "chunks.jsonl"

    run_parsing_stage(
        data_dir=input_dir,
        output_csv=str(cleaned_csv),
        output_jsonl=str(metadata_jsonl),
        logger=logger,
    )

    stats = process_metadata_jsonl(
        input_path=str(metadata_jsonl),
        output_jsonl=str(chunks_jsonl),
        output_csv=str(output_path / "chunks.csv"),
        output_stats=str(output_path / "chunking_stats.json"),
        target_size=int(cfg["target_size"]),
        soft_limit=int(cfg["soft_limit"]),
        hard_limit=int(cfg["hard_limit"]),
        progress_interval=int(cfg["progress_interval"]),
        logger=logger,
    )

    if run_embedding:
        run_indexing_stage(
            chunks_jsonl=str(chunks_jsonl),
            output_index_path=str(output_path / "faiss.idx"),
            output_id_mapping_path=str(output_path / "chunk_ids.json"),
            output_bm25_path=str(output_path / "bm25.pkl"),
            model_name=model_name,
            logger=logger,
        )

    return stats