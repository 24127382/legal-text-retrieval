from __future__ import annotations
import os
import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, Any, Optional, List
import pandas as pd

from src.schema import StructuralUnit, DocumentMetadata

# ============================================================
# REGEX PATTERNS
# ============================================================
ARTICLE_RE = re.compile(r"(?im)^\s*Điều\s+(\d+[A-Za-z]?)\s*[\.\:\-]?\s*(.*)$")
CLAUSE_RE = re.compile(r"(?m)^\s*(\d+)\s*[\.\)]\s+(.+)$")
POINT_RE = re.compile(r"(?m)^\s*([a-zđ])\s*[\.\)]\s+(.+)$", re.IGNORECASE)
CHAPTER_RE = re.compile(r"(?im)^\s*Chương\s+([IVXLCDM]+|\d+)\s*[\.\:\-]?\s*(.*)$")
SECTION_RE = re.compile(r"(?im)^\s*Mục\s+([IVXLCDM]+|\d+)\s*[\.\:\-]?\s*(.*)$")
PART_RE = re.compile(r"(?im)^\s*Phần\s+([IVXLCDM]+|\d+)\s*[\.\:\-]?\s*(.*)$")
DECIMAL_SECTION_RE = re.compile(r"(?m)^\s*(\d+\.\d+)\s+(.+)$")


# ============================================================
# DATA LOADERS & PREPROCESSOR
# ============================================================
def load_raw_documents(data_dir: str) -> List[Dict[str, Any]]:
    """Load JSON files from directory handling single or multi-doc schemas."""
    documents = []
    data_path = Path(data_dir)
    if not data_path.exists():
        raise FileNotFoundError(f"Directory not found: {data_dir}")

    for filename in os.listdir(data_path):
        if not filename.endswith(".json"):
            continue
        filepath = data_path / filename
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict) and "passage" in data and "id" in data:
            documents.append({
                "document_id": str(data["id"]),
                "cleaned_text": preprocess_single_document(data),
                "document_title": data.get("name", ""),
                "link": data.get("link", "")
            })
        elif isinstance(data, dict):
            for doc_id, doc in data.items():
                if isinstance(doc, dict) and "passage" in doc:
                    documents.append({
                        "document_id": str(doc.get("id", doc_id)),
                        "cleaned_text": preprocess_single_document(doc),
                        "document_title": doc.get("name", ""),
                        "link": doc.get("link", "")
                    })

    return [d for d in documents if d["cleaned_text"]]


def preprocess_single_document(doc: Dict[str, Any]) -> str:
    """Clean a single legal document conservatively."""
    content = doc.get("passage", "")
    if not content:
        return ""

    content = unicodedata.normalize("NFC", content)
    content = content.replace("\\", "")
    content = re.sub(r"\r\n?", "\n", content)
    content = content.replace("\t", " ")
    content = re.sub(r"^[=\-_*]{3,}\s*$", "", content, flags=re.MULTILINE)
    content = re.sub(r"[^\S\n]+", " ", content)
    content = re.sub(r"^[ \t]+|[ \t]+$", "", content, flags=re.MULTILINE)
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip()


# ============================================================
# STRUCTURAL EXTRACTION
# ============================================================
def clean_optional_title(title: Optional[str]) -> Optional[str]:
    if title is None:
        return None
    title = title.strip()
    return title if title else None


def detect_fingerprint(text: str) -> List[str]:
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


def extract_matches(text: str, pattern: re.Pattern, level: str) -> List[StructuralUnit]:
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
        units.extend(extract_matches(text=text, pattern=pattern, level=level))

    units.sort(key=lambda x: x.char_start)

    part_number = part_title = None
    chapter_number = chapter_title = None
    section_number = section_title = None

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