import json
import os
from typing import Any, Dict, List


def load_documents_from_dir(data_dir: str) -> List[Dict[str, Any]]:
    """Đọc và gom nhóm tất cả các tài liệu JSON từ thư mục dữ liệu."""
    documents = []

    for filename in os.listdir(data_dir):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(data_dir, filename)

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Case 1: Mỗi file = một document
        if (
            isinstance(data, dict)
            and "passage" in data
            and "id" in data
        ):
            documents.append({
                "id": str(data["id"]),
                "passage": data.get("passage", ""),
                "name": data.get("name", ""),
                "link": data.get("link", ""),
            })

        # Case 2: File chứa nhiều documents
        elif isinstance(data, dict):
            for doc_id, doc in data.items():
                if isinstance(doc, dict) and "passage" in doc:
                    documents.append({
                        "id": str(doc.get("id", doc_id)),
                        "passage": doc.get("passage", ""),
                        "name": doc.get("name", ""),
                        "link": doc.get("link", ""),
                    })

    return documents