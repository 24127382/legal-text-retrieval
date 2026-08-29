from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Optional

import pandas as pd
from src.schema.models import DocumentMetadata, StructuralUnit

# ============================================================
# REGEX PATTERNS
# ============================================================

# Điều 1 / Điều 1. / Điều 1:
ARTICLE_RE = re.compile(
    r"(?im)^\s*Điều\s+(\d+[A-Za-z]?)\s*[\.\:\-]?\s*(.*)$"
)

# Khoản: 1. Nội dung... / 2) Nội dung...
CLAUSE_RE = re.compile(r"(?m)^\s*(\d+)\s*[\.\)]\s+(.+)$")

# Điểm: a) Nội dung / b. Nội dung
POINT_RE = re.compile(r"(?m)^\s*([a-zđ])\s*[\.\)]\s+(.+)$", re.IGNORECASE)

# Chương I / Chương II
CHAPTER_RE = re.compile(
    r"(?im)^\s*Chương\s+([IVXLCDM]+|\d+)\s*[\.\:\-]?\s*(.*)$"
)

# Mục 1 / Mục I
SECTION_RE = re.compile(
    r"(?im)^\s*Mục\s+([IVXLCDM]+|\d+)\s*[\.\:\-]?\s*(.*)$"
)

# Phần I / Phần thứ nhất
PART_RE = re.compile(
    r"(?im)^\s*Phần\s+([IVXLCDM]+|\d+)\s*[\.\:\-]?\s*(.*)$"
)

# Decimal section: 1.1 / 1.2 / 2.1 ...
DECIMAL_SECTION_RE = re.compile(r"(?m)^\s*(\d+\.\d+)\s+(.+)$")


# ============================================================
# HELPERS
# ============================================================


def clean_optional_title(title: str | None) -> Optional[str]:
    if title is None:
        return None
    title = title.strip()
    return title if title else None


def detect_fingerprint(text: str) -> list[str]:
    """Detect những structural levels xuất hiện trong document."""
    fingerprint = []
    patterns = [
        ("part", PART_RE),
        ("chapter", CHAPTER_RE),
        ("section", SECTION_RE),
        ("article", ARTICLE_RE),
        ("clause", CLAUSE_RE),
        ("point", POINT_RE),
        ("decimal_section", DECIMAL_SECTION_RE),
    ]

    for name, pattern in patterns:
        if pattern.search(text):
            fingerprint.append(name)

    return fingerprint


def extract_matches(
    text: str,
    pattern: re.Pattern,
    level: str,
) -> list[StructuralUnit]:
    matches = list(pattern.finditer(text))
    units = []

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        groups = match.groups()

        number = groups[0] if len(groups) >= 1 else None
        title = groups[1] if len(groups) >= 2 else None

        units.append(
            StructuralUnit(
                level=level,
                number=number.strip() if number else None,
                title=clean_optional_title(title),
                char_start=start,
                char_end=end,
            )
        )

    return units


# ============================================================
# DOCUMENT PARSER
# ============================================================


def parse_document(
    document_id: str,
    text: str,
    document_title: Optional[str] = None,
) -> DocumentMetadata:
    text = text or ""
    fingerprint = detect_fingerprint(text)

    units = []
    patterns = [
        ("part", PART_RE),
        ("chapter", CHAPTER_RE),
        ("section", SECTION_RE),
        ("article", ARTICLE_RE),
        ("clause", CLAUSE_RE),
        ("point", POINT_RE),
        ("decimal_section", DECIMAL_SECTION_RE),
    ]

    for level, pattern in patterns:
        units.extend(
            extract_matches(
                text=text,
                pattern=pattern,
                level=level,
            )
        )

    # Sort by actual position in document
    units.sort(key=lambda x: x.char_start)

    part_number, part_title = None, None
    chapter_number, chapter_title = None, None
    section_number, section_title = None, None

    for unit in units:
        if unit.level == "part" and part_number is None:
            part_number, part_title = unit.number, unit.title
        elif unit.level == "chapter" and chapter_number is None:
            chapter_number, chapter_title = unit.number, unit.title
        elif unit.level == "section" and section_number is None:
            section_number, section_title = unit.number, unit.title

    return DocumentMetadata(
        document_id=document_id,
        document_title=document_title,
        part_number=part_number,
        part_title=part_title,
        chapter_number=chapter_number,
        chapter_title=chapter_title,
        section_number=section_number,
        section_title=section_title,
        fingerprint=fingerprint,
        units=units,
        text=text,
    )


# ============================================================
# PROCESS CSV TO JSONL
# ============================================================


def load_cleaned_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, low_memory=False)
    required_columns = {"document_id", "cleaned_text"}
    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    return df


def process_cleaned_csv(input_csv: str, output_jsonl: str) -> None:
    from dataclasses import asdict

    df = load_cleaned_data(input_csv)
    output_path = Path(output_jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total, failed = 0, 0

    with output_path.open("w", encoding="utf-8") as f:
        for row_idx, row in df.iterrows():
            try:
                document_id = str(row["document_id"])
                text = str(row["cleaned_text"]) if pd.notna(row["cleaned_text"]) else ""

                document_title = None
                if "document_title" in df.columns and pd.notna(row["document_title"]):
                    document_title = str(row["document_title"]).strip()

                metadata = parse_document(
                    document_id=document_id,
                    text=text,
                    document_title=document_title,
                )

                record = asdict(metadata)
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                total += 1

            except Exception as e:
                failed += 1
                print(f"[ERROR] row={row_idx}: {e}")

    print("=" * 60)
    print("METADATA EXTRACTION")
    print("=" * 60)
    print(f"Input rows : {len(df):,}")
    print(f"Processed   : {total:,}")
    print(f"Failed      : {failed:,}")
    print(f"Output      : {output_path}")