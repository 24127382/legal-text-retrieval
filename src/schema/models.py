from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class StructuralUnit:
    """Một đơn vị cấu trúc trong legal document.

    level: part / chapter / section / article / clause / point / fallback:
    paragraph number: Số/ký hiệu của structural unit, nếu detect được. title:
    Tiêu đề đi kèm, nếu có. char_start / char_end: Vị trí trong cleaned_text.
    """

    level: str
    number: Optional[str]
    title: Optional[str]
    char_start: int
    char_end: int


@dataclass
class DocumentMetadata:
    """Metadata ở cấp document."""

    document_id: str
    document_title: Optional[str]

    # High-level structure
    part_number: Optional[str]
    part_title: Optional[str]

    chapter_number: Optional[str]
    chapter_title: Optional[str]

    section_number: Optional[str]
    section_title: Optional[str]

    # Detected structural fingerprints
    fingerprint: list[str]

    # Structural units
    units: list[StructuralUnit]

    # Original cleaned text
    text: str