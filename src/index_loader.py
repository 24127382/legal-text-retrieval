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
        print(f"⏳ Đang khởi tạo Retriever từ Hugging Face Dataset: [{repo_id}]...")
        self.device = device
        
        # 1. Tải faiss.index và chunk_ids.json trực tiếp từ HF Hub
        index_file = hf_hub_download(repo_id=repo_id, filename="faiss.index", repo_type="dataset")
        ids_file = hf_hub_download(repo_id=repo_id, filename="chunk_ids.json", repo_type="dataset")
        
        # 2. Load FAISS Index & Chunk IDs Map
        self.index = faiss.read_index(index_file)
        with open(ids_file, "r", encoding="utf-8") as f:
            self.chunk_ids = json.load(f)
            
        # 3. Load Model Embeddings (để embed query)
        self.model = SentenceTransformer(model_name, device=self.device)
        self.model.max_seq_length = 1024

        # 4. Load dữ liệu nội dung văn bản (chunks.jsonl) từ local
        self.chunks_db = {}
        if Path(local_chunks_path).exists():
            with open(local_chunks_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        item = json.loads(line)
                        self.chunks_db[item["chunk_id"]] = item

        print(f"✔ Đã load thành công {self.index.ntotal:,} vectors!")

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Truy vấn Top-K chunks tương đồng nhất"""
        # Embed câu hỏi
        query_vector = self.model.encode(
            [query], 
            normalize_embeddings=True, 
            show_progress_bar=False
        )
        query_vector = np.array(query_vector, dtype=np.float32)

        # Tim kiếm trên FAISS
        scores, indices = self.index.search(query_vector, top_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.chunk_ids):
                continue
            
            chunk_id = self.chunk_ids[idx]
            chunk_data = self.chunks_db.get(chunk_id, {"chunk_id": chunk_id}).copy()
            chunk_data["score"] = float(score)
            results.append(chunk_data)
            
        return results

