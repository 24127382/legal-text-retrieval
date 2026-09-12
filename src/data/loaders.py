"""Strict, source-preserving readers for raw competition JSON data."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Callable, TypeVar

from .schemas import MISSING, CorpusDocument, LegalIRSample, LegalQASample


class DataSchemaError(ValueError):
    """Raised when an input is valid JSON but violates the observed schema."""


class _ObjectPairs(list[tuple[str, object]]):
    """Keep JSON object pairs so duplicate top-level sample IDs are not lost."""


_SampleT = TypeVar("_SampleT", LegalIRSample, LegalQASample)


def _decode_json(payload: bytes, source: str) -> object:
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DataSchemaError(f"{source}: input is not valid UTF-8: {exc}") from exc

    try:
        return json.loads(text, object_pairs_hook=_ObjectPairs)
    except json.JSONDecodeError as exc:
        raise DataSchemaError(f"{source}: invalid JSON: {exc}") from exc


def _read_json(path: Path) -> object:
    try:
        return _decode_json(path.read_bytes(), str(path))
    except OSError as exc:
        raise OSError(f"Could not read {path}: {exc}") from exc


def _fields(
    value: object,
    *,
    source: str,
    allowed: set[str],
) -> dict[str, object]:
    if not isinstance(value, _ObjectPairs):
        raise DataSchemaError(f"{source}: expected a JSON object")

    result: dict[str, object] = {}
    for key, field_value in value:
        if key in result:
            raise DataSchemaError(f"{source}: duplicate field {key!r}")
        if key not in allowed:
            raise DataSchemaError(f"{source}: unexpected field {key!r}")
        result[key] = field_value
    return result


def _optional_text(fields: dict[str, object], name: str, source: str) -> object:
    if name not in fields:
        return MISSING
    value = fields[name]
    if value is not None and not isinstance(value, str):
        raise DataSchemaError(
            f"{source}.{name}: expected string or null, got {type(value).__name__}"
        )
    return value


def _load_task(
    path: str | Path,
    parse_sample: Callable[[str, object, str], _SampleT],
) -> list[_SampleT]:
    input_path = Path(path)
    root = _read_json(input_path)
    if not isinstance(root, _ObjectPairs):
        raise DataSchemaError(f"{input_path}: expected a JSON object keyed by sample ID")

    samples: list[_SampleT] = []
    for sample_id, value in root:
        location = f"{input_path}[{sample_id!r}]"
        samples.append(parse_sample(sample_id, value, location))
    return samples


def _parse_legal_ir_sample(
    sample_id: str, value: object, source: str
) -> LegalIRSample:
    fields = _fields(value, source=source, allowed={"question", "answer"})
    question = _optional_text(fields, "question", source)
    answer = fields.get("answer", MISSING)
    if answer is not MISSING and answer is not None:
        if not isinstance(answer, list) or isinstance(answer, _ObjectPairs):
            raise DataSchemaError(
                f"{source}.answer: expected list of strings or null, "
                f"got {type(answer).__name__}"
            )
        for index, document_id in enumerate(answer):
            if not isinstance(document_id, str):
                raise DataSchemaError(
                    f"{source}.answer[{index}]: expected string, "
                    f"got {type(document_id).__name__}"
                )
    return LegalIRSample(sample_id=sample_id, question=question, answer=answer)


def _parse_legal_qa_sample(
    sample_id: str, value: object, source: str
) -> LegalQASample:
    fields = _fields(value, source=source, allowed={"question", "answer"})
    question = _optional_text(fields, "question", source)
    answer = _optional_text(fields, "answer", source)
    return LegalQASample(sample_id=sample_id, question=question, answer=answer)


def load_legal_ir(path: str | Path) -> list[LegalIRSample]:
    """Load a raw LegalIR JSON object without changing questions or labels."""

    return _load_task(path, _parse_legal_ir_sample)


def load_legal_qa(path: str | Path) -> list[LegalQASample]:
    """Load a raw LegalQA JSON object without changing questions or answers."""

    return _load_task(path, _parse_legal_qa_sample)


def _parse_corpus_document(value: object, source: str) -> CorpusDocument:
    fields = _fields(
        value,
        source=source,
        allowed={"id", "passage", "link", "name"},
    )

    if "id" not in fields:
        raise DataSchemaError(f"{source}: missing required field 'id'")
    document_id = fields["id"]
    if type(document_id) is not int:
        raise DataSchemaError(
            f"{source}.id: expected integer, got {type(document_id).__name__}"
        )

    if "link" not in fields:
        raise DataSchemaError(f"{source}: missing required field 'link'")
    link = fields["link"]
    if not isinstance(link, str):
        raise DataSchemaError(
            f"{source}.link: expected string, got {type(link).__name__}"
        )

    passage = _optional_text(fields, "passage", source)
    name = _optional_text(fields, "name", source)
    return CorpusDocument(id=document_id, passage=passage, link=link, name=name)


def _documents_from_json(value: object, source: str) -> list[CorpusDocument]:
    if isinstance(value, _ObjectPairs):
        return [_parse_corpus_document(value, source)]
    if isinstance(value, list):
        return [
            _parse_corpus_document(document, f"{source}[{index}]")
            for index, document in enumerate(value)
        ]
    raise DataSchemaError(f"{source}: expected a corpus document or list of documents")


def _load_corpus_zip(path: Path) -> list[CorpusDocument]:
    documents: list[CorpusDocument] = []
    try:
        with zipfile.ZipFile(path) as archive:
            members = sorted(
                (
                    info
                    for info in archive.infolist()
                    if not info.is_dir() and info.filename.lower().endswith(".json")
                ),
                key=lambda info: info.filename,
            )
            if not members:
                raise DataSchemaError(f"{path}: archive contains no JSON documents")
            for member in members:
                source = f"{path}!{member.filename}"
                documents.extend(
                    _documents_from_json(_decode_json(archive.read(member), source), source)
                )
    except zipfile.BadZipFile as exc:
        raise DataSchemaError(f"{path}: invalid ZIP archive: {exc}") from exc
    return documents


def load_corpus(path: str | Path) -> list[CorpusDocument]:
    """Load selected contexts from a ZIP, JSON file, or JSON directory.

    ZIP members and directory files are read in sorted name order. Archives are
    read directly and are never extracted.
    """

    input_path = Path(path)
    if input_path.is_dir():
        json_paths = sorted(
            candidate
            for candidate in input_path.rglob("*")
            if candidate.is_file() and candidate.suffix.lower() == ".json"
        )
        if not json_paths:
            raise DataSchemaError(f"{input_path}: directory contains no JSON documents")
        documents: list[CorpusDocument] = []
        for json_path in json_paths:
            documents.extend(_documents_from_json(_read_json(json_path), str(json_path)))
        return documents

    if not input_path.is_file():
        raise FileNotFoundError(f"Input path does not exist or is not a file: {input_path}")
    if input_path.suffix.lower() == ".zip":
        return _load_corpus_zip(input_path)
    if input_path.suffix.lower() == ".json":
        return _documents_from_json(_read_json(input_path), str(input_path))
    raise DataSchemaError(f"{input_path}: expected a .zip, .json, or directory input")
