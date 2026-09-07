import json
import logging
from pathlib import Path
from typing import List, Dict, Set, Optional
from tqdm import tqdm

from src.retriever import LegalRetriever

logger = logging.getLogger(__name__)

def evaluate_retrieval(
    train_file: str,
    index_file: str,
    id_mapping_file: str,
    bm25_file: Optional[str] = None,
    bm25_id_file: Optional[str] = None,
    raw_chunks_file: Optional[str] = None,
    mode: str = "hybrid",
    top_k_chunks: int = 20,
    top_k_docs: int = 5,
    sample_size: Optional[int] = None
):
    """
    Đánh giá độ chính xác của hệ thống.
    mode: 'faiss', 'bm25', 'hybrid', 'rerank'
    """
    logger.info(f"--- BẮT ĐẦU ĐÁNH GIÁ (Chế độ: {mode.upper()}) ---")
    
    logger.info("Đang nạp Retriever...")
    retriever = LegalRetriever(
        index_path=index_file, 
        id_mapping_path=id_mapping_file,
        bm25_path=bm25_file,
        bm25_id_path=bm25_id_file,
        raw_chunks_path=raw_chunks_file
    )
    
    train_path = Path(train_file)
    with train_path.open("r", encoding="utf-8") as f:
        test_data = json.load(f)
        
    if sample_size:
        # Lấy sample_size câu đầu tiên để test nhanh
        test_data = dict(list(test_data.items())[:sample_size])
        logger.info(f"Đã cắt lấy {sample_size} câu hỏi đầu tiên để đánh giá nhanh (vì Reranker chạy rất nặng).")
        
    logger.info(f"Đã nạp {len(test_data)} câu hỏi từ {train_path.name}")
    
    total_recall = 0.0
    total_precision = 0.0
    num_queries = len(test_data)
    
    for qid, qdata in tqdm(test_data.items(), desc="Đang đánh giá", total=num_queries):
        query = qdata.get("question", "")
        ground_truth: Set[str] = set(qdata.get("answer", []))
        
        if not ground_truth:
            continue
            
        if mode == "faiss":
            results = retriever.search_faiss(query, top_k=top_k_chunks)
        elif mode == "bm25":
            results = retriever.search_bm25(query, top_k=top_k_chunks)
        elif mode == "rerank":
            # Rerank lấy top 60 từ hybrid rồi chấm điểm lại, trả về top 5
            results = retriever.search_hybrid_rerank(query, top_k_retrieve=top_k_chunks, top_k_rerank=top_k_docs * 3)
        else:
            results = retriever.search_hybrid(query, top_k=top_k_chunks)
        
        unique_docs = []
        for res in results:
            doc_id = res["chunk_id"].split("_chunk_")[0]
            if doc_id not in unique_docs:
                unique_docs.append(doc_id)
            if len(unique_docs) == top_k_docs:
                break
                
        retrieved: Set[str] = set(unique_docs)
        
        true_positives = len(ground_truth.intersection(retrieved))
        recall = true_positives / len(ground_truth) if len(ground_truth) > 0 else 0.0
        precision = true_positives / len(retrieved) if len(retrieved) > 0 else 0.0
        
        total_recall += recall
        total_precision += precision

    avg_recall = total_recall / num_queries
    avg_precision = total_precision / num_queries
    
    if avg_recall + avg_precision > 0:
        f2_score = (5 * avg_precision * avg_recall) / (4 * avg_precision + avg_recall)
    else:
        f2_score = 0.0
        
    logger.info("========================================")
    logger.info(f"KẾT QUẢ ĐÁNH GIÁ (Mode: {mode.upper()}):")
    logger.info(f" 🎯 Recall@5    : {avg_recall:.4f} ({(avg_recall*100):.2f}%)")
    logger.info(f" 🎯 Precision@5 : {avg_precision:.4f} ({(avg_precision*100):.2f}%)")
    logger.info(f" ⭐ F2-Score    : {f2_score:.4f} ({(f2_score*100):.2f}%)")
    logger.info("========================================")
    
    return avg_recall, avg_precision, f2_score

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    
    TRAIN_FILE = "data/train.json"
    INDEX_FILE = "data/processed/faiss.idx"
    ID_FILE = "data/processed/chunk_ids.json"
    BM25_FILE = "data/processed/bm25.pkl"
    BM25_ID_FILE = "data/processed/bm25_chunk_ids.json"
    CHUNKS_FILE = "data/processed/chunks.jsonl"
    
    # Đánh giá Rerank (Bạn có thể đổi lại thành 'hybrid' nếu muốn)
    evaluate_retrieval(
        train_file=TRAIN_FILE,
        index_file=INDEX_FILE,
        id_mapping_file=ID_FILE,
        bm25_file=BM25_FILE,
        bm25_id_file=BM25_ID_FILE,
        raw_chunks_file=CHUNKS_FILE,
        mode="rerank",
        top_k_chunks=30, # Lấy 30 kết quả từ hybrid là đủ cho Reranker (lấy 100 quá tốn thời gian)
        top_k_docs=5,
        sample_size=300 # Test nhanh trên 300 câu hỏi
    )
