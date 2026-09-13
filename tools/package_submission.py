"""Validate an existing prediction JSON and package it at a ZIP archive root."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path


def read_json(path: Path):
    if not path.is_file():
        raise ValueError(f"file does not exist: {path}")
    try:
        with path.open(encoding="utf-8-sig") as stream:
            return json.load(stream)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc


def validate_expected_ids(prediction_ids: set[str], expected_ids_path: Path) -> None:
    expected = read_json(expected_ids_path)
    if isinstance(expected, dict):
        expected_values = list(expected)
    elif isinstance(expected, list):
        if not all(
            isinstance(value, (str, int)) and not isinstance(value, bool)
            for value in expected
        ):
            raise ValueError("expected-ID list must contain only string or integer IDs")
        expected_values = [str(value) for value in expected]
    else:
        raise ValueError("expected-ID file must contain a JSON object or ID list")

    if len(expected_values) != len(set(expected_values)):
        raise ValueError("expected-ID file contains duplicate IDs")

    expected_ids = set(expected_values)
    if prediction_ids != expected_ids:
        missing = sorted(expected_ids - prediction_ids)[:10]
        unexpected = sorted(prediction_ids - expected_ids)[:10]
        raise ValueError(
            "prediction IDs do not exactly match expected test IDs; "
            f"missing={missing}, unexpected={unexpected}"
        )


def validate_legalir(predictions: object) -> set[str]:
    if not isinstance(predictions, dict):
        raise ValueError("LegalIR predictions must be a top-level JSON object")
    if not predictions:
        raise ValueError("LegalIR predictions must not be empty")

    identifier_type: type | None = None
    for sample_id, sample in predictions.items():
        if not isinstance(sample, dict):
            raise ValueError(f"sample {sample_id!r}: value must be an object")
        if "answer" not in sample:
            raise ValueError(f"sample {sample_id!r}: missing answer")
        answer = sample["answer"]
        if not isinstance(answer, list):
            raise ValueError(f"sample {sample_id!r}: answer must be a list")
        if not 1 <= len(answer) <= 5:
            raise ValueError(f"sample {sample_id!r}: answer length must be between 1 and 5")

        for document_id in answer:
            if not isinstance(document_id, (str, int)) or isinstance(document_id, bool):
                raise ValueError(
                    f"sample {sample_id!r}: document IDs must be strings or integers"
                )
            if isinstance(document_id, str) and not document_id:
                raise ValueError(f"sample {sample_id!r}: document IDs must not be empty")
            current_type = type(document_id)
            if identifier_type is None:
                identifier_type = current_type
            elif current_type is not identifier_type:
                raise ValueError("document IDs must use one consistent JSON type")

        if len(answer) != len(set(answer)):
            raise ValueError(f"sample {sample_id!r}: answer contains duplicate IDs")

    return set(predictions)


def validate_legalqa(predictions: object) -> set[str]:
    if not isinstance(predictions, dict):
        raise ValueError("LegalQA predictions must be a top-level JSON object")
    if not predictions:
        raise ValueError("LegalQA predictions must not be empty")

    for sample_id, sample in predictions.items():
        if not isinstance(sample, dict):
            raise ValueError(f"sample {sample_id!r}: value must be an object")
        if "answer" not in sample:
            raise ValueError(f"sample {sample_id!r}: missing answer")
        if not isinstance(sample["answer"], str):
            raise ValueError(f"sample {sample_id!r}: answer must be a string")

    return set(predictions)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a prediction JSON and place it at the root of a ZIP."
    )
    parser.add_argument("prediction_json", type=Path)
    parser.add_argument("output_zip", type=Path)
    parser.add_argument("--task", choices=("legalir", "legalqa"), default="legalir")
    parser.add_argument(
        "--expected-ids",
        type=Path,
        help="optional JSON object or list containing the exact expected test IDs",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.prediction_json.suffix.lower() != ".json":
        raise ValueError("prediction path must end with .json")
    predictions = read_json(args.prediction_json)
    prediction_ids = (
        validate_legalir(predictions)
        if args.task == "legalir"
        else validate_legalqa(predictions)
    )
    if args.expected_ids is not None:
        validate_expected_ids(prediction_ids, args.expected_ids)

    if args.output_zip.suffix.lower() != ".zip":
        raise ValueError("output path must end with .zip")
    if not args.output_zip.parent.is_dir():
        raise ValueError(f"output directory does not exist: {args.output_zip.parent}")

    with zipfile.ZipFile(
        args.output_zip, mode="w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        archive.write(args.prediction_json, arcname=args.prediction_json.name)

    print(f"Created {args.output_zip} with root entry {args.prediction_json.name}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        raise SystemExit(f"error: {exc}") from exc
