import logging
import os
from src.pipeline import run_full_pipeline

# Cấu hình log để theo dõi tiến độ trên màn hình
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    # Thư mục chứa 8532 file JSON thô của BTC
    INPUT_DIR = os.path.join("data", "selected-contexts", "selected-contexts")
    
    # Thư mục lưu kết quả sau khi băm
    OUTPUT_DIR = os.path.join("data", "processed")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    logger.info("🚀 BẮT ĐẦU QUÁ TRÌNH TIỀN XỬ LÝ DỮ LIỆU (LOCAL) 🚀")
    logger.info(f"Đọc dữ liệu từ: {INPUT_DIR}")
    logger.info(f"Lưu kết quả tại: {OUTPUT_DIR}")
    
    # Gọi hàm chạy toàn bộ quy trình, nhớ set run_embedding=False
    # vì bước Embedding sẽ mang lên Google Colab chạy cho lẹ
    stats = run_full_pipeline(
        input_dir=INPUT_DIR,
        output_dir=OUTPUT_DIR,
        run_embedding=False,
        logger=logger
    )
    
    logger.info("🎉 XONG! BẠN CÓ THỂ MANG FILE 'chunks.jsonl' TRONG THƯ MỤC 'data/processed' LÊN COLAB RỒI!")

if __name__ == "__main__":
    main()
