"""Small loaders for the raw competition JSON files."""

import json
from pathlib import Path


def _read_json(path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"JSON file does not exist: {path}")

    try:
        with path.open(encoding="utf-8-sig") as stream:
            return json.load(stream)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc


def load_legal_ir(path: str | Path) -> dict:
    """Load a LegalIR JSON object without changing its contents."""

    data = _read_json(Path(path))
    if not isinstance(data, dict) or not all(
        isinstance(sample, dict) for sample in data.values()
    ):
        raise ValueError(f"{path}: expected an object keyed by sample ID")
    return data


def load_legal_qa(path: str | Path) -> dict:
    """Load a LegalQA JSON object without changing its contents."""

    data = _read_json(Path(path))
    if not isinstance(data, dict) or not all(
        isinstance(sample, dict) for sample in data.values()
    ):
        raise ValueError(f"{path}: expected an object keyed by sample ID")
    return data


def _corpus_documents(data, source: str) -> list[dict]:
    if isinstance(data, dict):
        documents = [data]
    elif isinstance(data, list):
        documents = data
    else:
        raise ValueError(f"{source}: expected a document or list of documents")

    if not all(isinstance(document, dict) for document in documents):
        raise ValueError(f"{source}: every corpus document must be an object")
    return documents


def load_corpus(path: str | Path) -> list[dict]:
    """Load corpus documents from a JSON file or directory."""

    input_path = Path(path)
    if input_path.is_dir():
        json_paths = sorted(
            candidate
            for candidate in input_path.rglob("*")
            if candidate.is_file() and candidate.suffix.lower() == ".json"
        )
        if not json_paths:
            raise ValueError(f"{input_path}: directory contains no JSON files")

        documents = []
        for json_path in json_paths:
            documents.extend(_corpus_documents(_read_json(json_path), str(json_path)))
        return documents

    if not input_path.is_file():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")
    if input_path.suffix.lower() == ".json":
        return _corpus_documents(_read_json(input_path), str(input_path))
    raise ValueError(f"{input_path}: expected a JSON file or directory")
