import json
import logging
import zipfile
from pathlib import Path
from tqdm import tqdm

from src.retriever import LegalRetriever

logger = logging.getLogger(__name__)

def generate_submission(
    test_file: str,
    index_file: str,
    id_mapping_file: str,
    bm25_file: str,
    bm25_id_file: str,
    output_dir: str = "output",
    top_k_chunks: int = 60,
    top_k_docs: int = 5
):
    """
    Đọc file đề thi public-official.json, dự đoán và xuất ra file submission.json & submission.zip
    """
    logger.info("--- BẮT ĐẦU GIẢI ĐỀ THI (SUBMISSION GENERATOR) ---")
    
    # 1. Khởi tạo Hybrid Retriever
    retriever = LegalRetriever(
        index_path=index_file, 
        id_mapping_path=id_mapping_file,
        bm25_path=bm25_file,
        bm25_id_path=bm25_id_file
    )
    
    # 2. Đọc đề thi
    test_path = Path(test_file)
    if not test_path.exists():
        raise FileNotFoundError(f"Không tìm thấy đề thi: {test_path}")
        
    with test_path.open("r", encoding="utf-8") as f:
        test_data = json.load(f)
        
    logger.info(f"Đã nạp {len(test_data)} câu hỏi từ {test_path.name}")
    
    # 3. Tiến hành giải từng câu
    submission_dict = {}
    
    for qid, qdata in tqdm(test_data.items(), desc="Đang giải đề", total=len(test_data)):
        query = qdata.get("question", "")
        
        # Dùng Hybrid Search RRF
        results = retriever.search_hybrid(query, top_k=top_k_chunks)
        
        # Bóc tách và lọc lấy Top 5 Document ID độc nhất
        unique_docs = []
        for res in results:
            doc_id = res["chunk_id"].split("_chunk_")[0]
            if doc_id not in unique_docs:
                unique_docs.append(doc_id)
            if len(unique_docs) == top_k_docs:
                break
                
        # Cấu trúc JSON object theo yêu cầu BTC
        submission_dict[qid] = {
            "answer": unique_docs
        }

    # 4. Lưu ra file JSON
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    json_out_path = out_dir / "submission.json"
    logger.info(f"Đang xuất file JSON ra: {json_out_path}")
    
    with json_out_path.open("w", encoding="utf-8") as f:
        json.dump(submission_dict, f, ensure_ascii=False, indent=2)
        
    # 5. Đóng gói ZIP chuẩn Zalo AI (Chỉ chứa submission.json bên trong)
    zip_out_path = out_dir / "submission.zip"
    logger.info(f"Đang nén file ZIP ra: {zip_out_path}")
    
    with zipfile.ZipFile(zip_out_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # ARC_NAME là 'submission.json' để giải nén ra nó không bị dính cái folder
        zipf.write(json_out_path, arcname="submission.json")
        
    logger.info("=============================================")
    logger.info("🎉 HOÀN TẤT GIẢI ĐỀ! BẠN CÓ THỂ ĐEM ĐI NỘP RỒI!")
    logger.info(f"📁 Đường dẫn file nộp: {zip_out_path}")
    logger.info("=============================================")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    
    # Cấu hình đường dẫn
    TEST_FILE = "data/public-official.json"
    INDEX_FILE = "data/processed/faiss.index"
    ID_FILE = "data/processed/chunk_ids.json"
    BM25_FILE = "data/processed/bm25.pkl"
    BM25_ID_FILE = "data/processed/bm25_chunk_ids.json"
    
    generate_submission(
        test_file=TEST_FILE,
        index_file=INDEX_FILE,
        id_mapping_file=ID_FILE,
        bm25_file=BM25_FILE,
        bm25_id_file=BM25_ID_FILE,
        output_dir="output",
        top_k_chunks=60,
        top_k_docs=5
    )
