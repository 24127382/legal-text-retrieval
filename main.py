import sys
from pathlib import Path

# Đảm bảo Python nhận diện được thư mục src
sys.path.append(str(Path(__file__).parent / "src"))

from src.legal_chunker import process_metadata_jsonl

if __name__ == "__main__":
    process_metadata_jsonl(
        input_path="/kaggle/working/output/document_metadata.jsonl",
        output_jsonl="output/chunks.jsonl",
        output_csv="output/chunks.csv",
        output_stats="output/chunking_stats.json",
    )