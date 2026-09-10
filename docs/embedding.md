# `index_loader.py` — Remote Legal Retriever

## 1. Purpose

`index_loader.py` cung cấp interface để thực hiện **semantic retrieval** cho Vietnamese Legal RAG.

Module này chịu trách nhiệm:

```text
Hugging Face Dataset
        │
        ├── faiss.index
        └── chunk_ids.json
                │
                ▼
        HFLegalRetriever
                │
        ┌───────┴────────┐
        │                │
   BGE-M3 Model    Local chunks.jsonl
        │                │
        └───────┬────────┘
                ▼
           FAISS Search
                │
                ▼
        Top-K Legal Chunks
```

Module giúp tách biệt:

* **Offline Embedding & Indexing:** chạy trên GPU.
* **Online Retrieval:** chạy trên CPU local.

FAISS index được lưu trên Hugging Face thay vì đưa trực tiếp vào GitHub. Cách này tránh việc repository phải chứa file binary lớn và cho phép application tự động tải index khi cần.

---

# 2. Source Files

Retriever sử dụng ba thành phần chính:

### Remote — Hugging Face Dataset

```text
faiss.index
chunk_ids.json
```

Hai file này được tải tự động thông qua `hf_hub_download()`.

### Local

```text
output/chunks.jsonl
```

File này chứa nội dung và metadata của các chunks.

### Embedding Model

```text
BAAI/bge-m3
```

Model được load local để biến query của người dùng thành vector trước khi tìm kiếm trên FAISS.

---

# 3. `HFLegalRetriever`

## 3.1. Initialization

```python
class HFLegalRetriever:
    def __init__(
        self,
        repo_id: str = "Akiya-Vyre/legal-text-embedding",
        model_name: str = "BAAI/bge-m3",
        local_chunks_path: str = "output/chunks.jsonl",
        device: str = "cpu"
    ):
```

### Parameters

| Parameter           | Default                           | Description                           |
| ------------------- | --------------------------------- | ------------------------------------- |
| `repo_id`           | `Akiya-Vyre/legal-text-embedding` | Hugging Face Dataset chứa FAISS index |
| `model_name`        | `BAAI/bge-m3`                     | Embedding model dùng cho query        |
| `local_chunks_path` | `output/chunks.jsonl`             | Local database chứa chunk content     |
| `device`            | `cpu`                             | Device chạy embedding model           |

---

# 4. Loading FAISS Index

Retriever tự động tải:

```python
index_file = hf_hub_download(
    repo_id=repo_id,
    filename="faiss.index",
    repo_type="dataset"
)

ids_file = hf_hub_download(
    repo_id=repo_id,
    filename="chunk_ids.json",
    repo_type="dataset"
)
```

Sau đó load:

```python
self.index = faiss.read_index(index_file)

with open(ids_file, "r", encoding="utf-8") as f:
    self.chunk_ids = json.load(f)
```

Flow:

```text
Hugging Face
     │
     ├── faiss.index
     │       ↓
     │   faiss.read_index()
     │
     └── chunk_ids.json
             ↓
        self.chunk_ids
```

`hf_hub_download()` có cơ chế caching nên index không cần tải lại toàn bộ mỗi lần application khởi động nếu file đã tồn tại trong cache.

---

# 5. Loading Embedding Model

Query cần được chuyển thành vector trước khi FAISS có thể search.

```python
self.model = SentenceTransformer(
    model_name,
    device=self.device
)

self.model.max_seq_length = 1024
```

Model mặc định:

```text
BAAI/bge-m3
```

Query embedding sử dụng:

```python
normalize_embeddings=True
```

để vector được L2-normalize, phù hợp với FAISS `IndexFlatIP` đã sử dụng trong quá trình indexing.

---

# 6. Loading Local Chunks

FAISS chỉ trả về vector index và vị trí tương ứng.

Do đó application cần `chunks.jsonl` để lấy lại nội dung thực tế của chunk.

```python
self.chunks_db = {}

if Path(local_chunks_path).exists():
    with open(local_chunks_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                self.chunks_db[item["chunk_id"]] = item
```

Data được lưu thành dictionary:

```text
chunk_id → chunk_data
```

Ví dụ:

```text
{
    "chunk_001": {...},
    "chunk_002": {...},
    "chunk_003": {...}
}
```

---

# 7. Search

Interface chính của retriever:

```python
results = retriever.search(
    query,
    top_k=5
)
```

## 7.1. Query → Embedding

```python
query_vector = self.model.encode(
    [query],
    normalize_embeddings=True,
    show_progress_bar=False
)

query_vector = np.array(
    query_vector,
    dtype=np.float32
)
```

Flow:

```text
User Query
    │
    ▼
BGE-M3
    │
    ▼
Normalized Query Vector
```

---

## 7.2. FAISS Search

```python
scores, indices = self.index.search(
    query_vector,
    top_k
)
```

FAISS trả về:

```text
scores
indices
```

Trong đó:

* `indices` = vị trí vector trong FAISS index.
* `scores` = similarity score.

---

## 7.3. FAISS Index → Chunk ID

Retriever sử dụng `indices` để lấy `chunk_id`:

```python
chunk_id = self.chunk_ids[idx]
```

Sau đó dùng `chunk_id` để lấy content:

```python
chunk_data = self.chunks_db.get(
    chunk_id,
    {"chunk_id": chunk_id}
).copy()
```

Cuối cùng thêm similarity score:

```python
chunk_data["score"] = float(score)
```

Flow đầy đủ:

```text
Query
  │
  ▼
BGE-M3
  │
  ▼
Query Vector
  │
  ▼
FAISS
  │
  ├── score
  └── index
       │
       ▼
  chunk_ids.json
       │
       ▼
    chunk_id
       │
       ▼
chunks.jsonl
       │
       ▼
Chunk Content + Metadata + Score
```

---

# 8. Return Format

`search()` trả về:

```python
List[Dict[str, Any]]
```

Mỗi result có dạng tương tự:

```python
{
    "chunk_id": "some_chunk_id",
    "text": "...legal text...",
    "score": 0.8234
}
```

Các metadata khác có trong `chunks.jsonl` cũng được giữ lại.

---

# 9. Complete `index_loader.py`

```python
import json
from pathlib import Path
from typing import List, Dict, Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from huggingface_hub import hf_hub_download


class HFLegalRetriever:
    def __init__(
        self,
        repo_id: str = "Akiya-Vyre/legal-text-embedding",
        model_name: str = "BAAI/bge-m3",
        local_chunks_path: str = "output/chunks.jsonl",
        device: str = "cpu"
    ):
        print(
            f"⏳ Đang khởi tạo Retriever từ Hugging Face Dataset: "
            f"[{repo_id}]..."
        )

        self.device = device

        # 1. Download FAISS index and chunk ID mapping
        index_file = hf_hub_download(
            repo_id=repo_id,
            filename="faiss.index",
            repo_type="dataset"
        )

        ids_file = hf_hub_download(
            repo_id=repo_id,
            filename="chunk_ids.json",
            repo_type="dataset"
        )

        # 2. Load FAISS index and chunk IDs
        self.index = faiss.read_index(index_file)

        with open(ids_file, "r", encoding="utf-8") as f:
            self.chunk_ids = json.load(f)

        # 3. Load embedding model
        self.model = SentenceTransformer(
            model_name,
            device=self.device
        )

        self.model.max_seq_length = 1024

        # 4. Load local chunk database
        self.chunks_db = {}

        if Path(local_chunks_path).exists():
            with open(local_chunks_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        item = json.loads(line)
                        self.chunks_db[item["chunk_id"]] = item

        print(
            f"✔ Đã load thành công {self.index.ntotal:,} vectors!"
        )

    def search(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Truy vấn Top-K chunks tương đồng nhất."""

        # 1. Embed query
        query_vector = self.model.encode(
            [query],
            normalize_embeddings=True,
            show_progress_bar=False
        )

        query_vector = np.array(
            query_vector,
            dtype=np.float32
        )

        # 2. Search FAISS
        scores, indices = self.index.search(
            query_vector,
            top_k
        )

        # 3. Map FAISS index -> chunk_id -> chunk data
        results = []

        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.chunk_ids):
                continue

            chunk_id = self.chunk_ids[idx]

            chunk_data = self.chunks_db.get(
                chunk_id,
                {"chunk_id": chunk_id}
            ).copy()

            chunk_data["score"] = float(score)

            results.append(chunk_data)

        return results
```

---

# 10. Usage

Import retriever:

```python
from index_loader import HFLegalRetriever
```

Initialize:

```python
retriever = HFLegalRetriever(
    repo_id="Akiya-Vyre/legal-text-embedding",
    model_name="BAAI/bge-m3",
    local_chunks_path="output/chunks.jsonl",
    device="cpu"
)
```

Retriever sẽ tự động:

1. Kết nối tới Hugging Face Dataset.
2. Download/cache `faiss.index`.
3. Download/cache `chunk_ids.json`.
4. Load BGE-M3.
5. Load `output/chunks.jsonl`.

Cách sử dụng này được định nghĩa trực tiếp trong tài liệu pipeline hiện tại.

---

# 11. Performing a Search

Ví dụ:

```python
query = "Quy định về xử phạt vi phạm hành chính trong lĩnh vực thuế"

results = retriever.search(
    query,
    top_k=3
)
```

Print results:

```python
for i, res in enumerate(results, 1):
    print(
        f"[{i}] Chunk ID: "
        f"{res['chunk_id']} | "
        f"Score: {res['score']:.4f}"
    )

    print(
        f"    Nội dung: "
        f"{res.get('text', '')[:150]}...\n"
    )
```

Output conceptually:

```text
[1] Chunk ID: ... | Score: 0.8234
    Nội dung: ...

[2] Chunk ID: ... | Score: 0.8012
    Nội dung: ...

[3] Chunk ID: ... | Score: 0.7845
    Nội dung: ...
```

---

# 12. Architecture Summary

`index_loader.py` hiện tại đóng vai trò **Semantic Retriever Interface**:

```text
                 Hugging Face
                      │
             ┌────────┴────────┐
             │                 │
        faiss.index      chunk_ids.json
             │                 │
             └────────┬────────┘
                      │
                      ▼
              HFLegalRetriever
                      │
          ┌───────────┴───────────┐
          │                       │
       BGE-M3              chunks.jsonl
          │                       │
          ▼                       │
      Query Vector                │
          │                       │
          ▼                       │
        FAISS                     │
          │                       │
          ▼                       │
      Top-K IDs ──────────────────┘
              │
              ▼
       Chunk + Metadata
              │
              ▼
          RAG Context
```

### Hardware Separation

```text
OFFLINE
────────────────────────────
Chunks
   ↓
BGE-M3
   ↓
FAISS Index
   ↓
Upload to Hugging Face

       GPU
        │
        ▼

ONLINE
────────────────────────────
User Query
   ↓
BGE-M3
   ↓
FAISS Search
   ↓
Top-K Chunks
   ↓
LLM

       CPU
```

Thiết kế này cho phép phần **indexing nặng** chạy một lần trên GPU, trong khi application chỉ cần thực hiện **query embedding + FAISS retrieval** trên CPU local. Tài liệu đặt mục tiêu latency retrieval online khoảng **10–30 ms**.
