from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

REQUIRED_FIELDS = [
    "document_id", "chunk_id", "chunk_index", "document_title",
    "part_number", "part_title", "chapter_number", "chapter_title",
    "section_number", "section_title", "articles", "clauses", "points",
    "char_start", "char_end", "char_length", "chunk_type", "is_split", "text"
]

NON_EMPTY_FIELDS = ["document_id", "chunk_id", "text", "chunk_type"]


def is_strict_int(val: Any) -> bool:
    return type(val) is int


def load_source_documents(source_path: str | Path) -> Dict[str, Dict[str, Any]]:
    source_docs = {}
    path = Path(source_path)
    if not path.exists():
        print(f"⚠️ [WARN] Không tìm thấy source file tại '{source_path}'. Bỏ qua kiểm tra Source & Structural Boundary.")
        return source_docs

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                doc = json.loads(line_str)
                doc_id = str(doc.get("document_id") or doc.get("id") or "")
                if doc_id:
                    source_docs[doc_id] = doc
            except json.JSONDecodeError:
                continue
    print(f"✅ Đã load thành công {len(source_docs):,} văn bản nguồn vào memory.")
    return source_docs


def validate_chunks_v021(
    chunks_path: str | Path = "output/chunks.jsonl",
    source_path: str | Path = "output/metadata.jsonl",
    stats_path: str | Path = "output/chunking_stats.json",
    max_reported_errors: int = 20
) -> Tuple[bool, List[str]]:
    """
    Thực hiện Audit 5 Layer toàn vẹn dữ liệu Chunks V0.2.1.
    Trả về: (passed: bool, errors: List[str])
    """
    path = Path(chunks_path)
    if not path.exists():
        msg = f"❌ [ERROR] File chunks không tồn tại: {chunks_path}"
        print(msg)
        return False, [msg]

    source_docs = load_source_documents(source_path)
    if not source_docs:
        msg = "❌ [ERROR] Cần file SOURCE_FILE để đối chiếu nội dung và ranh giới cấu trúc!"
        print(msg)
        return False, [msg]

    seen_chunk_ids: Set[str] = set()
    doc_chunk_history: Dict[str, List[Dict[str, Any]]] = {}

    total_lines = 0
    json_parse_errors = 0
    errors: List[str] = []
    structural_boundary_errors = 0
    source_mismatch_errors = 0
    whitespace_gaps_ignored = 0

    length_buckets = Counter({
        "<1000": 0, "1k-3k": 0, "3k-5k": 0, "5k-5.5k": 0, "5.5k-6k": 0, ">6k": 0
    })

    with path.open("r", encoding="utf-8") as f:
        for line_idx, line in enumerate(f, start=1):
            line_str = line.strip()
            if not line_str:
                continue

            total_lines += 1

            # LAYER 1: JSON Syntax & Basic Schema
            try:
                record: Dict[str, Any] = json.loads(line_str)
            except json.JSONDecodeError as exc:
                json_parse_errors += 1
                errors.append(f"Dòng {line_idx}: JSON Syntax Error - {exc}")
                continue

            chunk_id = record.get("chunk_id", f"Line_{line_idx}")

            missing_fields = [f for f in REQUIRED_FIELDS if f not in record]
            if missing_fields:
                errors.append(f"Dòng {line_idx} ({chunk_id}): Thiếu trường: {missing_fields}")

            for f_name in NON_EMPTY_FIELDS:
                val = record.get(f_name)
                if val is None or (isinstance(val, str) and not val.strip()):
                    errors.append(f"Dòng {line_idx} ({chunk_id}): Trường '{f_name}' RỖNG/NULL")

            chunk_idx = record.get("chunk_index")
            c_start = record.get("char_start")
            c_end = record.get("char_end")
            c_len = record.get("char_length")
            doc_id = str(record.get("document_id", ""))
            text = record.get("text", "")

            if not is_strict_int(chunk_idx):
                errors.append(f"Dòng {line_idx} ({chunk_id}): `chunk_index` không phải int chuẩn")
            if not is_strict_int(c_start):
                errors.append(f"Dòng {line_idx} ({chunk_id}): `char_start` không phải int chuẩn")
            if not is_strict_int(c_end):
                errors.append(f"Dòng {line_idx} ({chunk_id}): `char_end` không phải int chuẩn")
            if not is_strict_int(c_len):
                errors.append(f"Dòng {line_idx} ({chunk_id}): `char_length` không phải int chuẩn")

            if chunk_id in seen_chunk_ids:
                errors.append(f"Dòng {line_idx}: Trùng lặp `chunk_id` -> '{chunk_id}'")
            else:
                seen_chunk_ids.add(chunk_id)

            # LAYER 2: Internal Offset Integrity
            if is_strict_int(c_start) and is_strict_int(c_end) and is_strict_int(c_len):
                if c_start < 0:
                    errors.append(f"Dòng {line_idx} ({chunk_id}): `char_start` âm ({c_start})")
                if c_end <= c_start:
                    errors.append(f"Dòng {line_idx} ({chunk_id}): `char_end` ({c_end}) <= `char_start` ({c_start})")

                expected_span = c_end - c_start
                if c_len != expected_span:
                    errors.append(f"Dòng {line_idx} ({chunk_id}): Lệch `char_length`! Khai báo={c_len}, (end-start)={expected_span}")

                if len(text) != c_len:
                    errors.append(f"Dòng {line_idx} ({chunk_id}): Lệch len(text)! Actual={len(text)} vs char_length={c_len}")

            # LAYER 3: Source Integrity Check
            if doc_id in source_docs and is_strict_int(c_start) and is_strict_int(c_end):
                src_text = source_docs[doc_id].get("cleaned_text") or source_docs[doc_id].get("text", "")
                expected_text = src_text[c_start:c_end]
                if text != expected_text:
                    source_mismatch_errors += 1
                    errors.append(
                        f"Dòng {line_idx} ({chunk_id}): SOURCE MISMATCH! "
                        f"Chunk text không khớp với source_text[{c_start}:{c_end}]."
                    )

            # LAYER 4: Hard Structural Boundary Check
            if doc_id in source_docs and is_strict_int(c_start) and is_strict_int(c_end):
                units = source_docs[doc_id].get("units", [])
                struct_units = [u for u in units if u.get("level") in ("part", "chapter", "section")]
                for u in struct_units:
                    u_start = u.get("char_start", -1)
                    if c_start < u_start < c_end:
                        structural_boundary_errors += 1
                        errors.append(
                            f"Dòng {line_idx} ({chunk_id}): HARD BOUNDARY VIOLATION! "
                            f"Chunk chứa ranh giới {u.get('level').upper()} '{u.get('number')}' tại offset {u_start} (chunk range: {c_start} -> {c_end})"
                        )

            # LAYER 5: Distribution Tracker
            if is_strict_int(c_len):
                if c_len < 1000: length_buckets["<1000"] += 1
                elif 1000 <= c_len < 3000: length_buckets["1k-3k"] += 1
                elif 3000 <= c_len < 5000: length_buckets["3k-5k"] += 1
                elif 5000 <= c_len <= 5500: length_buckets["5k-5.5k"] += 1
                elif 5500 < c_len <= 6000: length_buckets["5.5k-6k"] += 1
                else: length_buckets[">6k"] += 1

            if doc_id and is_strict_int(chunk_idx) and is_strict_int(c_start) and is_strict_int(c_end):
                doc_chunk_history.setdefault(doc_id, []).append({
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_idx,
                    "char_start": c_start,
                    "char_end": c_end,
                    "line_idx": line_idx
                })

    # BOUNDARY INTEGRITY & CONTINUITY CHECK
    for d_id, chunks in doc_chunk_history.items():
        actual_indices = [c["chunk_index"] for c in chunks]
        expected_indices = list(range(len(chunks)))
        if actual_indices != expected_indices:
            errors.append(f"Văn bản '{d_id}': Trật tự `chunk_index` không liên tục: {actual_indices[:5]}...")

        if d_id in source_docs:
            src_text = source_docs[d_id].get("cleaned_text") or source_docs[d_id].get("text", "")
            for i in range(1, len(chunks)):
                prev_chunk = chunks[i - 1]
                curr_chunk = chunks[i]
                prev_end = prev_chunk["char_end"]
                curr_start = curr_chunk["char_start"]

                if prev_end != curr_start:
                    if curr_start > prev_end:
                        gap_content = src_text[prev_end:curr_start]
                        if gap_content.strip() == "":
                            whitespace_gaps_ignored += 1
                        else:
                            errors.append(
                                f"Văn bản '{d_id}': MẤT CHỮ giữa {prev_chunk['chunk_id']} và {curr_chunk['chunk_id']}! "
                                f"Lỗi rớt {len(gap_content)} chars: {repr(gap_content)}"
                            )
                    else:
                        overlap_size = prev_end - curr_start
                        errors.append(
                            f"Văn bản '{d_id}': OVERLAP {overlap_size} chars giữa {prev_chunk['chunk_id']} và {curr_chunk['chunk_id']}!"
                        )

    # STATS FILE VERIFICATION
    failed_docs_count = 0
    sp_path = Path(stats_path)
    if sp_path.exists():
        with sp_path.open("r", encoding="utf-8") as sf:
            stats_data = json.load(sf)
            failed_docs_count = stats_data.get("failed_documents", 0)
            if failed_docs_count > 0:
                errors.append(f"STATS ERROR: Phát hiện {failed_docs_count} document bị lỗi xử lý (`failed_documents` > 0)")
    else:
        errors.append(f"STATS ERROR: Không tìm thấy file thống kê tại '{stats_path}'")

    # IN BÁO CÁO SANITY CHECK
    print("\n" + "=" * 70)
    print(f" 🛡️  BÁO CÁO SANITY CHECK V0.2.1 FULL AUDIT: {path.name}")
    print("=" * 70)
    print(f"Tổng số chunk kiểm tra        : {total_lines:,}")
    print(f"Số GAP khoảng trắng bỏ qua   : {whitespace_gaps_ignored:,} (Hợp lệ)")
    print(f"TỔNG SỐ LỖI NGHIÊM TRỌNG       : {len(errors):,}")
    print("-" * 70)

    print("📊 PHÂN BỐ ĐỘ DÀI CHUNK:")
    for bucket, count in length_buckets.items():
        pct = (count / total_lines * 100) if total_lines > 0 else 0
        bar = "█" * int(pct // 2)
        print(f"  {bucket:<8}: {count:>6,} chunks ({pct:>5.1f}%) | {bar}")
    print("-" * 70)

    chunks_over_6k = length_buckets[">6k"]
    print("🏆 BẢNG ĐỐI CHIẾU 4 CHỈ SỐ VÀNG V0.2.1:")
    print(f"  1. Source Integrity      : {'PASSED (0 errors)' if source_mismatch_errors == 0 else f'FAILED ({source_mismatch_errors} errors)'}")
    print(f"  2. Boundary Integrity    : {'PASSED (0 errors)' if len(errors) - source_mismatch_errors - structural_boundary_errors == 0 else 'FAILED'}")
    print(f"  3. Hard Structural Bound : {'PASSED (0 errors)' if structural_boundary_errors == 0 else f'FAILED ({structural_boundary_errors} violations)'}")
    print(f"  4. Chunks > 6000         : {'PASSED (0 chunks)' if chunks_over_6k == 0 else f'FAILED ({chunks_over_6k} chunks)'}")
    print(f"  5. Failed Documents      : {'PASSED (0 docs)' if failed_docs_count == 0 else f'FAILED ({failed_docs_count} docs)'}")
    print("-" * 70)

    if errors:
        print(f"❌ KẾT QUẢ: FAILED ({len(errors)} lỗi cần xử lý)")
        print(f"Danh sách lỗi đầu tiên (Top {max_reported_errors}):")
        for err in errors[:max_reported_errors]:
            print(f"  • {err}")
        if len(errors) > max_reported_errors:
            print(f"  ... và còn {len(errors) - max_reported_errors} lỗi khác.")
        return False, errors

    print("🔒 KẾT QUẢ: PASSED ALL INVARIANTS 100%! ĐỦ ĐIỀU KIỆN ĐÓNG DẤU V0.2.1.")
    return True, []