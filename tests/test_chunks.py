from pathlib import Path
from src.validator import validate_chunks_v021


def test_chunking_integrity():
    """Kiểm tra toàn vẹn dữ liệu chunks trong thư mục output."""
    chunks_file = Path("output/chunks.jsonl")
    metadata_file = Path("output/metadata.jsonl")
    stats_file = Path("output/chunking_stats.json")

    assert chunks_file.exists(), f"File {chunks_file} chưa được tạo. Hãy chạy main.py trước!"
    assert metadata_file.exists(), f"File {metadata_file} không tồn tại!"

    passed, errors = validate_chunks_v021(
        chunks_path=chunks_file,
        source_path=metadata_file,
        stats_path=stats_file,
    )

    assert passed, f"Sanity Check Thất Bại với {len(errors)} lỗi: {errors[:3]}"