from dataclasses import dataclass
from typing import Optional


@dataclass
class ChunkRecord:
    document_id: str
    chunk_id: str
    chunk_index: int

    document_title: Optional[str]

    part_number: Optional[str]
    part_title: Optional[str]

    chapter_number: Optional[str]
    chapter_title: Optional[str]

    section_number: Optional[str]
    section_title: Optional[str]

    articles: list[str]
    clauses: list[str]
    points: list[str]

    char_start: int
    char_end: int

    text: str


@dataclass
class ChunkUnit:
    level: str
    number: Optional[str]
    text: str
    char_start: int
    char_end: int
    articles: list[str]
    clauses: list[str]
    points: list[str]