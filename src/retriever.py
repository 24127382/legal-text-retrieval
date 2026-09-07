import json
import logging
import pickle
from pathlib import Path
from typing import List, Dict, Optional

import faiss
import numpy as np
import torch
from pyvi import ViTokenizer
from sentence_transformers import SentenceTransformer, CrossEncoder

logger = logging.getLogger(__name__)

class LegalRetriever:
    """
    Công cụ tìm kiếm văn bản pháp luật hỗ trợ 3 chế độ: FAISS, BM25, và HYBRID (RRF).
    """
    def __init__(
        self,
        index_path: str,
        id_mapping_path: str,
        bm25_path: Optional[str] = None,
        bm25_id_path: Optional[str] = None,
        model_name: str = "BAAI/bge-m3",
        reranker_name: Optional[str] = "BAAI/bge-reranker-v2-m3",
        raw_chunks_path: Optional[str] = None,
        device: Optional[str] = None
    ):
        self.index_path = Path(index_path)
        self.id_mapping_path = Path(id_mapping_path)
        
        # 1. LOAD FAISS (DENSE RETRIEVAL)
        if not self.index_path.exists() or not self.id_mapping_path.exists():
            raise FileNotFoundError("Không tìm thấy dữ liệu FAISS Index!")

        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        logger.info(f"Đang tải FAISS index...")
        self.index = faiss.read_index(str(self.index_path))
        
        with self.id_mapping_path.open("r", encoding="utf-8") as f:
            self.chunk_ids = json.load(f)

        logger.info(f"Đang khởi tạo mô hình Embedding {model_name} trên {self.device.upper()}...")
        self.model = SentenceTransformer(model_name, device=self.device)
        
        # 2. LOAD BM25 (SPARSE RETRIEVAL)
        self.bm25 = None
        self.bm25_chunk_ids = None
        
        if bm25_path and bm25_id_path:
            p_bm25 = Path(bm25_path)
            p_bm25_id = Path(bm25_id_path)
            if p_bm25.exists() and p_bm25_id.exists():
                logger.info(f"Đang tải BM25 index...")
                with p_bm25.open("rb") as f:
                    self.bm25 = pickle.load(f)
                with p_bm25_id.open("r", encoding="utf-8") as f:
                    self.bm25_chunk_ids = json.load(f)
            else:
                logger.warning("Không tìm thấy file BM25, sẽ bỏ qua chế độ Hybrid.")
                
        # 3. LOAD RERANKER (CROSS-ENCODER)
        self.reranker = None
        self.raw_chunks_text = None
        if reranker_name:
            logger.info(f"Đang tải mô hình Reranker {reranker_name} trên {self.device.upper()}...")
            self.reranker = CrossEncoder(reranker_name, device=self.device)
            # Chúng ta cần load file chunks.jsonl vào bộ nhớ RAM để Reranker có thể lấy lại nội dung text gốc
            
            if raw_chunks_path:
                chunks_path = Path(raw_chunks_path)
            else:
                chunks_path = self.id_mapping_path.parent / "chunks.jsonl"
                
            if chunks_path.exists():
                logger.info(f"Đang nạp file {chunks_path.name} vào bộ nhớ (cần cho Reranker)...")
                self.raw_chunks_text = {}
                with chunks_path.open("r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            record = json.loads(line)
                            self.raw_chunks_text[record["chunk_id"]] = record["text"]
            else:
                logger.warning(f"Không tìm thấy {chunks_path}. Tính năng Rerank sẽ không hoạt động nếu thiếu Text gốc.")
                
        logger.info("✔ Hệ thống tìm kiếm (Retriever) đã sẵn sàng!")

    def search_faiss(self, query: str, top_k: int = 5) -> List[Dict[str, float]]:
        if not query.strip(): return []
        
        query_embedding = self.model.encode(
            query,
            show_progress_bar=False,
            normalize_embeddings=True
        )
        query_vector = np.array([query_embedding], dtype=np.float32)
        scores, indices = self.index.search(query_vector, top_k)
        
        results = []
        for i in range(top_k):
            idx = indices[0][i]
            if idx != -1 and idx < len(self.chunk_ids):
                results.append({
                    "chunk_id": self.chunk_ids[idx],
                    "score": float(scores[0][i])
                })
        return results

    def search_bm25(self, query: str, top_k: int = 5) -> List[Dict[str, float]]:
        if not self.bm25 or not query.strip(): return []
        
        # Tách từ tiếng Việt giống như lúc Build Index
        tokenized_query = ViTokenizer.tokenize(query.lower()).split()
        
        # Lấy điểm số BM25 cho toàn bộ corpus
        doc_scores = self.bm25.get_scores(tokenized_query)
        
        # Lấy top_k kết quả cao nhất
        top_indices = np.argsort(doc_scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            score = doc_scores[idx]
            if score > 0: # Chỉ lấy các kết quả có chứa từ khóa
                results.append({
                    "chunk_id": self.bm25_chunk_ids[idx],
                    "score": float(score)
                })
        return results

    def search_hybrid(self, query: str, top_k: int = 5, k_rrf: int = 60) -> List[Dict[str, float]]:
        """
        Tìm kiếm lai bằng thuật toán Reciprocal Rank Fusion (RRF).
        RRF Score = 1 / (k_rrf + rank_faiss) + 1 / (k_rrf + rank_bm25)
        """
        if not self.bm25:
            return self.search_faiss(query, top_k)
            
        # Lấy nhiều kết quả hơn (ví dụ Top 60) từ mỗi phương pháp để dễ giao thoa
        faiss_results = self.search_faiss(query, top_k=60)
        bm25_results = self.search_bm25(query, top_k=60)
        
        # Gộp điểm RRF
        rrf_scores = {}
        
        # Xử lý FAISS
        for rank, res in enumerate(faiss_results, 1):
            chunk_id = res["chunk_id"]
            if chunk_id not in rrf_scores:
                rrf_scores[chunk_id] = 0.0
            rrf_scores[chunk_id] += 1.0 / (k_rrf + rank)
            
        # Xử lý BM25
        for rank, res in enumerate(bm25_results, 1):
            chunk_id = res["chunk_id"]
            if chunk_id not in rrf_scores:
                rrf_scores[chunk_id] = 0.0
            rrf_scores[chunk_id] += 1.0 / (k_rrf + rank)
            
        # Sắp xếp lại theo điểm RRF giảm dần
        sorted_rrf = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Lấy Top K cuối cùng
        results = []
        for chunk_id, score in sorted_rrf[:top_k]:
            results.append({
                "chunk_id": chunk_id,
                "score": score
            })
            
        return results

    def search_hybrid_rerank(self, query: str, top_k_retrieve: int = 60, top_k_rerank: int = 5) -> List[Dict[str, float]]:
        """
        Tìm kiếm lai (Hybrid) sau đó Rerank lại bằng Cross-Encoder.
        """
        if not self.reranker or not self.raw_chunks_text:
            logger.warning("Reranker hoặc Raw Text không khả dụng. Chuyển về Hybrid RRF.")
            return self.search_hybrid(query, top_k=top_k_rerank)
            
        # 1. Lấy Top N bằng Hybrid (RRF)
        hybrid_results = self.search_hybrid(query, top_k=top_k_retrieve)
        
        # 2. Xây dựng cặp (Query, Document) để đưa vào Cross-Encoder
        pairs = []
        valid_chunks = []
        for res in hybrid_results:
            chunk_id = res["chunk_id"]
            if chunk_id in self.raw_chunks_text:
                text = self.raw_chunks_text[chunk_id]
                pairs.append([query, text])
                valid_chunks.append(chunk_id)
                
        if not pairs:
            return hybrid_results[:top_k_rerank]
            
        # 3. Tính điểm Reranker
        # Mặc định CrossEncoder trả về mảng điểm số logits (float)
        scores = self.reranker.predict(pairs)
        
        # 4. Gắn điểm và sắp xếp lại
        reranked_results = []
        for chunk_id, score in zip(valid_chunks, scores):
            reranked_results.append({
                "chunk_id": chunk_id,
                "score": float(score)
            })
            
        # Sắp xếp giảm dần theo điểm Reranker
        reranked_results = sorted(reranked_results, key=lambda x: x["score"], reverse=True)
        
        return reranked_results[:top_k_rerank]

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    
    DATA_DIR = Path("data/processed")
    INDEX_FILE = DATA_DIR / "faiss.index"
    ID_FILE = DATA_DIR / "chunk_ids.json"
    BM25_FILE = DATA_DIR / "bm25.pkl"
    BM25_ID_FILE = DATA_DIR / "bm25_chunk_ids.json"
    
    if INDEX_FILE.exists() and ID_FILE.exists() and BM25_FILE.exists():
        retriever = LegalRetriever(
            str(INDEX_FILE), str(ID_FILE),
            str(BM25_FILE), str(BM25_ID_FILE)
        )
        
        query = "Nghị định 100 phạt vượt đèn đỏ bao nhiêu?"
        print(f"\n❓ Câu hỏi: {query}")
        
        print("\n--- KẾT QUẢ FAISS ---")
        for rank, res in enumerate(retriever.search_faiss(query, top_k=3), 1):
            print(f" {rank}. [{res['chunk_id']}] - Score: {res['score']:.4f}")
            
        print("\n--- KẾT QUẢ BM25 ---")
        for rank, res in enumerate(retriever.search_bm25(query, top_k=3), 1):
            print(f" {rank}. [{res['chunk_id']}] - Score: {res['score']:.4f}")
            
        print("\n--- KẾT QUẢ HYBRID (RRF) ---")
        for rank, res in enumerate(retriever.search_hybrid(query, top_k=3), 1):
            print(f" {rank}. [{res['chunk_id']}] - Score: {res['score']:.4f}")
            
        print("\n--- KẾT QUẢ HYBRID + RERANK ---")
        for rank, res in enumerate(retriever.search_hybrid_rerank(query, top_k_retrieve=30, top_k_rerank=3), 1):
            print(f" {rank}. [{res['chunk_id']}] - Score: {res['score']:.4f}")
    else:
        print("Vui lòng chạy bm25_builder.py trước khi test.")
