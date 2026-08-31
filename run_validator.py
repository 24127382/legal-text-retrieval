import argparse
import sys
from pathlib import Path
from src.validator import validate_chunks_v021


def main():
    parser = argparse.ArgumentParser(description="Chạy Sanity Check Audit cho Chunks V0.2.1.")
    parser.add_argument("--chunks", default="output/chunks.jsonl", help="Đường dẫn file chunks.jsonl")
    parser.add_argument("--source", default="output/metadata.jsonl", help="Đường dẫn file metadata.jsonl")
    parser.add_argument("--stats", default="output/chunking_stats.json", help="Đường dẫn file chunking_stats.json")

    args = parser.parse_args()

    passed, _ = validate_chunks_v021(
        chunks_path=args.chunks,
        source_path=args.source,
        stats_path=args.stats
    )

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()