import re
import unicodedata
from typing import Any, Dict


def preprocess_single_document(doc: Dict[str, Any]) -> str:
    """Clean a single legal document conservatively."""
    content = doc.get("passage", "")

    if not content:
        return ""

    # 1. Unicode normalization
    content = unicodedata.normalize("NFC", content)

    # 2. Remove known export/escape artifact
    content = content.replace("\\", "")

    # 3. Normalize line endings
    content = re.sub(r"\r\n?", "\n", content)

    # 4. Normalize tabs
    content = content.replace("\t", " ")

    # 5. Remove standalone separator/layout lines
    content = re.sub(
        r"^[=\-_*]{3,}\s*$", "", content, flags=re.MULTILINE
    )

    # 6. Collapse horizontal whitespace
    content = re.sub(r"[^\S\n]+", " ", content)

    # 7. Remove leading/trailing spaces from each line
    content = re.sub(
        r"^[ \t]+|[ \t]+$", "", content, flags=re.MULTILINE
    )

    # 8. Limit excessive blank lines
    content = re.sub(r"\n{3,}", "\n\n", content)

    # 9. Final trim
    return content.strip()