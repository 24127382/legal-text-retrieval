import json
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer


def generate_chunk_embeddings(
    input_jsonl: str = "output/chunks.jsonl",
    output_parquet: str = "output/embedded_chunks.parquet",
    model_name: str = "BAAI/bge-m3",
    batch_size: int = 32,
):
    input_path = Path(input_jsonl)
    output_path = Path(output_parquet)

    if not input_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {input_path}")

    # 1. Load Chunks
    print(f"📦 Đang đọc dữ liệu từ {input_path}...")
    chunks = []
    with input_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))

    print(f"✔ Đã load {len(chunks):,} chunks.")

    # 2. Extract Data
    chunk_ids = [c["chunk_id"] for c in chunks]
    doc_ids = [c["document_id"] for c in chunks]
    texts = [c["text"] for c in chunks]

    # 3. Load Model Embedding
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🚀 Đang tải model {model_name} trên thiết bị [{device.upper()}]...")
    model = SentenceTransformer(model_name, device=device)

    # 4. Generate Embeddings
    print("⏳ Đang tính toán Vector Embeddings...")
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,  # Trả về Cosine Similarity space
    )

    # 5. Lưu kết quả dưới dạng Parquet (Tối ưu dung lượng và tốc độ truy vấn)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(
        {
            "chunk_id": chunk_ids,
            "document_id": doc_ids,
            "embedding": list(embeddings),
        }
    )
    df.to_parquet(output_path, index=False)

    # Lưu thêm 1 bản numpy array thuần nếu cần dùng FAISS trực tiếp
    np.save(output_path.parent / "embeddings_matrix.npy", embeddings)

    print("==========================================")
    print("🎉 HOÀN TẤT TẠO VECTOR SPACE!")
    print(f" File lưu DataFrame  : {output_path}")
    print(f" File lưu Matrix Numpy: {output_path.parent / 'embeddings_matrix.npy'}")
    print(f" Kích thước Vector   : {embeddings.shape} (Chunks x Dimensions)")
    print("==========================================")


if __name__ == "__main__":
    generate_chunk_embeddings()