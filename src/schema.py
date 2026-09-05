from dataclasses import dataclass
from typing import Optional, List

@dataclass
class StructuralUnit:
    """Represents a single structural unit in a legal document."""
    level: str
    number: Optional[str]
    title: Optional[str]
    char_start: int
    char_end: int

@dataclass
class DocumentMetadata:
    """Document-level metadata and structural extraction outputs."""
    document_id: str
    document_title: Optional[str]
    document_link: Optional[str]
    text: str
    units: List[StructuralUnit]
    fingerprint: List[str]
    
@dataclass
class ChunkRecord:
    document_id: str
    chunk_id: str
    chunk_index: int
    document_title: Optional[str]
    document_link: Optional[str]
    part_number: Optional[str]
    part_title: Optional[str]
    chapter_number: Optional[str]
    chapter_title: Optional[str]
    section_number: Optional[str]
    section_title: Optional[str]
    articles: List[str]
    clauses: List[str]
    points: List[str]
    char_start: int
    char_end: int
    char_length: int
    chunk_type: str
    is_split: bool
    text: str

@dataclass
class ChunkUnit:
    level: str
    number: Optional[str]
    text: str
    char_start: int
    char_end: int
    articles: List[str]
    clauses: List[str]
    points: List[str]
    part_number: Optional[str] = None
    part_title: Optional[str] = None
    chapter_number: Optional[str] = None
    chapter_title: Optional[str] = None
    section_number: Optional[str] = None
    section_title: Optional[str] = None

    @property
    def context_key(self) -> tuple:
        return (self.part_number, self.chapter_number, self.section_number)