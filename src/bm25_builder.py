import json
import logging
import pickle
from pathlib import Path
from pyvi import ViTokenizer
from rank_bm25 import BM25Okapi
from tqdm import tqdm

logger = logging.getLogger(__name__)

def build_bm25_index(chunks_file: str, output_model: str, output_ids: str):
    """
    Đọc chunks.jsonl, tách từ tiếng Việt bằng PyVi và xây dựng BM25 Index.
    """
    logger.info("--- BẮT ĐẦU XÂY DỰNG BM25 INDEX ---")
    
    input_path = Path(chunks_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file chunks: {input_path}")
        
    chunks = []
    logger.info("Đang nạp dữ liệu từ chunks.jsonl...")
    with input_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
                
    logger.info(f"Đã nạp {len(chunks)} chunks. Tiến hành Tách từ (Tokenization) bằng PyVi...")
    
    chunk_ids = []
    tokenized_corpus = []
    
    for c in tqdm(chunks, desc="Tokenizing"):
        chunk_ids.append(c["chunk_id"])
        
        # Tiền xử lý cơ bản: Chuyển chữ thường, tách từ tiếng Việt
        text = c["text"].lower()
        tokens = ViTokenizer.tokenize(text).split()
        tokenized_corpus.append(tokens)
        
    logger.info("Đang huấn luyện mô hình BM25Okapi...")
    bm25 = BM25Okapi(tokenized_corpus)
    
    logger.info("Đang lưu mô hình xuống ổ cứng...")
    out_model_path = Path(output_model)
    out_ids_path = Path(output_ids)
    
    out_model_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Lưu BM25 model
    with out_model_path.open("wb") as f:
        pickle.dump(bm25, f)
        
    # Lưu chunk_ids để mapping kết quả
    with out_ids_path.open("w", encoding="utf-8") as f:
        json.dump(chunk_ids, f, ensure_ascii=False, indent=2)
        
    logger.info("==========================================")
    logger.info("🎉 HOÀN TẤT XÂY DỰNG BM25 INDEX!")
    logger.info(f"File BM25: {out_model_path}")
    logger.info(f"File IDs : {out_ids_path}")
    logger.info("==========================================")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    build_bm25_index(
        chunks_file="data/processed/chunks.jsonl",
        output_model="data/processed/bm25.pkl",
        output_ids="data/processed/bm25_chunk_ids.json"
    )
