"""Deterministic LegalIR split helpers."""

from hashlib import sha256


def make_legalir_split(samples: dict) -> dict[str, list[str]]:
    """Assign exact-question groups to the fixed LegalIR split-v1 buckets."""

    split_ids = {"train": [], "dev": [], "holdout": []}
    for sample_id, sample in samples.items():
        canonical_id = str(sample_id)
        question = sample.get("question")
        group_key = (
            question
            if isinstance(question, str)
            else f"\0fallback-sample-id:{canonical_id}"
        )
        bucket = int(sha256(group_key.encode("utf-8")).hexdigest()[:8], 16) % 100
        split = "train" if bucket < 70 else "dev" if bucket < 85 else "holdout"
        split_ids[split].append(canonical_id)

    for ids in split_ids.values():
        ids.sort()
    return split_ids


def select_samples(samples: dict, sample_ids: list[str]) -> dict:
    """Select a manifest-defined subset while preserving manifest ID order."""

    canonical_samples = {str(sample_id): sample for sample_id, sample in samples.items()}
    missing = [sample_id for sample_id in sample_ids if sample_id not in canonical_samples]
    if missing:
        raise KeyError(f"sample IDs are absent from source data: {missing[:5]}")
    return {sample_id: canonical_samples[sample_id] for sample_id in sample_ids}
