"""Validate predictions and package the fixed Codabench submission payload."""

from __future__ import annotations

import argparse
import json
import zipfile
from collections import Counter
from pathlib import Path

ARCHIVE_ENTRY = "submission.json"


def reject_duplicate_object_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON object key: {key!r}")
        value[key] = item
    return value


def read_json(path: Path):
    if not path.is_file():
        raise ValueError(f"file does not exist: {path}")
    try:
        with path.open(encoding="utf-8-sig") as stream:
            return json.load(stream, object_pairs_hook=reject_duplicate_object_keys)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc


def validate_expected_ids(
    prediction_ids: set[str], expected_ids_path: Path
) -> dict[str, int | bool]:
    expected = read_json(expected_ids_path)
    if not isinstance(expected, dict):
        raise TypeError(
            "expected-ID file must be the official phase input JSON object"
        )

    expected_ids = set(expected)
    missing_count = len(expected_ids - prediction_ids)
    extra_count = len(prediction_ids - expected_ids)
    exact_match = missing_count == 0 and extra_count == 0
    counts: dict[str, int | bool] = {
        "expected_ids": len(expected_ids),
        "prediction_ids": len(prediction_ids),
        "missing_count": missing_count,
        "extra_count": extra_count,
        "exact_match": exact_match,
    }
    if not exact_match:
        raise ValueError(
            "prediction IDs do not exactly match expected test IDs; "
            f"expected IDs={counts['expected_ids']}, "
            f"prediction IDs={counts['prediction_ids']}, "
            f"missing count={missing_count}, extra count={extra_count}"
        )
    return counts


def validate_legalir(predictions: object) -> tuple[set[str], Counter[int]]:
    if not isinstance(predictions, dict):
        raise TypeError("LegalIR predictions must be a top-level JSON object")
    if not predictions:
        raise ValueError("LegalIR predictions must not be empty")

    for sample_id, sample in predictions.items():
        if not isinstance(sample, dict):
            raise TypeError(f"sample {sample_id!r}: value must be an object")
        if set(sample) != {"answer"}:
            raise ValueError(
                f"sample {sample_id!r}: value must contain exactly the answer field"
            )
        answer = sample["answer"]
        if not isinstance(answer, list):
            raise TypeError(f"sample {sample_id!r}: answer must be a list")
        if not 1 <= len(answer) <= 5:
            raise ValueError(f"sample {sample_id!r}: answer length must be between 1 and 5")

        for document_id in answer:
            if not isinstance(document_id, str):
                raise TypeError(f"sample {sample_id!r}: document IDs must be strings")
            if not document_id:
                raise ValueError(f"sample {sample_id!r}: document IDs must not be empty")

        if len(answer) != len(set(answer)):
            raise ValueError(f"sample {sample_id!r}: answer contains duplicate IDs")

    return set(predictions), Counter(
        len(sample["answer"]) for sample in predictions.values()
    )


def validate_legalqa(predictions: object) -> set[str]:
    if not isinstance(predictions, dict):
        raise TypeError("LegalQA predictions must be a top-level JSON object")
    if not predictions:
        raise ValueError("LegalQA predictions must not be empty")

    for sample_id, sample in predictions.items():
        if not isinstance(sample, dict):
            raise TypeError(f"sample {sample_id!r}: value must be an object")
        if "answer" not in sample:
            raise ValueError(f"sample {sample_id!r}: missing answer")
        if not isinstance(sample["answer"], str):
            raise TypeError(f"sample {sample_id!r}: answer must be a string")

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
        required=True,
        help="official phase input JSON object containing the exact expected test IDs",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.prediction_json.suffix.lower() != ".json":
        raise ValueError("prediction path must end with .json")
    predictions = read_json(args.prediction_json)
    if args.task == "legalir":
        prediction_ids, answer_lengths = validate_legalir(predictions)
    else:
        prediction_ids = validate_legalqa(predictions)
        answer_lengths = None
    id_validation = validate_expected_ids(prediction_ids, args.expected_ids)

    if args.output_zip.suffix.lower() != ".zip":
        raise ValueError("output path must end with .zip")
    if not args.output_zip.parent.is_dir():
        raise ValueError(f"output directory does not exist: {args.output_zip.parent}")

    with zipfile.ZipFile(
        args.output_zip, mode="w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        archive.write(args.prediction_json, arcname=ARCHIVE_ENTRY)

    with zipfile.ZipFile(args.output_zip, mode="r") as archive:
        entries = archive.namelist()
        if entries != [ARCHIVE_ENTRY]:
            raise ValueError(
                f"archive entries must be exactly [{ARCHIVE_ENTRY!r}], got {entries!r}"
            )
        try:
            archived_predictions = json.loads(
                archive.read(ARCHIVE_ENTRY).decode("utf-8-sig"),
                object_pairs_hook=reject_duplicate_object_keys,
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid archived {ARCHIVE_ENTRY}: {exc}") from exc
    if archived_predictions != predictions:
        raise ValueError("archived submission payload differs from validated source JSON")

    print(f"task: {args.task}")
    print(f"samples: {len(predictions)}")
    print(f"archive: {args.output_zip}")
    print(f"archive entries: {json.dumps(entries)}")
    if answer_lengths is not None:
        distribution = {
            str(length): answer_lengths[length] for length in sorted(answer_lengths)
        }
        print(f"answer lengths: {json.dumps(distribution, sort_keys=True)}")
        print("all document IDs strings: true")
    print(f"expected IDs: {id_validation['expected_ids']}")
    print(f"prediction IDs: {id_validation['prediction_ids']}")
    print(f"missing count: {id_validation['missing_count']}")
    print(f"extra count: {id_validation['extra_count']}")
    print("expected IDs exact match: true")
    print("ready for Codabench: true")


if __name__ == "__main__":
    try:
        main()
    except (OSError, TypeError, ValueError) as exc:
        raise SystemExit(f"error: {exc}") from exc
