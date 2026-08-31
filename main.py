import argparse
import logging
from pathlib import Path
from typing import Any, Dict

import yaml
from src.pipeline import run_full_pipeline, run_parsing_stage, process_metadata_jsonl


def load_yaml_config(path: str) -> Dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Chạy Pipeline Xử lý & Chunking Văn Bản Pháp Lý End-to-End.")
    parser.add_argument("--config", type=str, default="configs/default.yaml", help="Đường dẫn file YAML config.")
    parser.add_argument("--input-dir", type=str, help="Ghi đè thư mục chứa dữ liệu JSON gốc.")
    parser.add_argument("--output-dir", type=str, help="Ghi đè thư mục kết quả xuất ra.")
    parser.add_argument("--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    args = parser.parse_args()

    # Cấu hình logging
    logging.basicConfig(level=getattr(logging, args.log_level.upper()), format="%(asctime)s - %(levelname)s - %(message)s")
    logger = logging.getLogger("legal_pipeline")

    try:
        yaml_cfg = load_yaml_config(args.config)
        pipeline_cfg = yaml_cfg.get("pipeline", {})
        chunking_cfg = yaml_cfg.get("chunking", {})

        # Lấy tham số (ưu tiên CLI args > YAML config)
        input_dir = args.input_dir or pipeline_cfg.get("input_dir", "data/raw")
        output_dir = args.output_dir or pipeline_cfg.get("output_dir", "output")

        logger.info("Bắt đầu chạy luồng xử lý...")
        run_full_pipeline(
            input_dir=input_dir,
            output_dir=output_dir,
            config=chunking_cfg,
            logger=logger,
        )
        return 0
    except Exception as exc:
        logger.error("Pipeline thất bại: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())