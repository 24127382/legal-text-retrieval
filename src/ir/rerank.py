"""Zero-shot cross-encoder reranking over fixed BM25 document candidates."""

import argparse
import importlib.util
import json
from collections.abc import Callable
from hashlib import sha256
from math import isfinite
from pathlib import Path
from time import perf_counter

import bm25s
import numpy as np
import torch
import transformers
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from src.corpus import chunk_corpus
from src.data import load_corpus, load_legal_ir
from src.ir.aggregate import aggregate_documents
from src.ir.bm25 import build_bm25, lexical_tokenize
from src.ir.evaluation import (
    compare_official_style_top_5,
    evaluate_retrieval,
    make_legalir_predictions,
    summarize_first_gold_ranks,
)
from src.ir.split import make_legalir_split, select_samples

MODEL_NAME = "BAAI/bge-reranker-v2-m3"
MODEL_REVISION = "953dc6f"
MODEL_RESOLVED_REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
TOP_K_CHUNKS = 2_000
CANDIDATE_DEPTH = 100
SUPPORTING_CHUNKS_PER_DOCUMENT = 2
MAX_SEQUENCE_LENGTH_CAP = 8_192


def load_reranker(
    model_name: str = MODEL_NAME,
    revision: str = MODEL_REVISION,
    device: str | None = None,
    model_path: str | Path | None = None,
) -> dict:
    """Load the fixed reranker from Hugging Face cache or Hub."""

    selected_device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    if selected_device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available")
    model_dtype = torch.float16 if selected_device.startswith("cuda") else torch.float32
    model_source = str(Path(model_path).resolve()) if model_path is not None else model_name
    revision_arguments = {} if model_path is not None else {"revision": revision}

    started = perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(
        model_source,
        **revision_arguments,
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        model_source,
        dtype=model_dtype,
        **revision_arguments,
    )
    model.to(selected_device)
    model.eval()

    resolved_revision = (
        Path(model_path).resolve().name
        if model_path is not None
        else getattr(model.config, "_commit_hash", None)
    )
    if resolved_revision != MODEL_RESOLVED_REVISION:
        raise RuntimeError(
            f"model resolved to unexpected revision {resolved_revision!r}"
        )

    tokenizer_limit = int(tokenizer.model_max_length)
    model_limit = int(getattr(model.config, "max_position_embeddings", tokenizer_limit))
    max_sequence_length = min(
        tokenizer_limit,
        model_limit,
        MAX_SEQUENCE_LENGTH_CAP,
    )
    if max_sequence_length <= 0:
        raise ValueError("resolved maximum sequence length must be positive")

    return {
        "model": model,
        "tokenizer": tokenizer,
        "model_name": model_name,
        "requested_revision": revision,
        "resolved_revision": resolved_revision,
        "device": selected_device,
        "dtype": str(model_dtype).removeprefix("torch."),
        "max_sequence_length": max_sequence_length,
        "load_seconds": perf_counter() - started,
    }


def build_fixed_candidates(
    index: dict,
    chunks: list[dict],
    samples: dict,
    top_k_chunks: int = TOP_K_CHUNKS,
    candidate_depth: int = CANDIDATE_DEPTH,
    batch_size: int = 64,
) -> dict:
    """Build top-100 sum-top-2 documents with their best two BM25 chunks."""

    if top_k_chunks <= 0:
        raise ValueError("top_k_chunks must be greater than zero")
    if candidate_depth <= 0:
        raise ValueError("candidate_depth must be greater than zero")
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")
    if top_k_chunks > index["number_of_chunks"]:
        raise ValueError("top_k_chunks cannot exceed the number of indexed chunks")
    if len(chunks) != index["number_of_chunks"]:
        raise ValueError("chunks must be the exact sequence used to build the index")

    sample_items = list(samples.items())
    candidates_by_query = {}
    started = perf_counter()

    for batch_start in range(0, len(sample_items), batch_size):
        batch = sample_items[batch_start : batch_start + batch_size]
        query_tokens = []
        for sample_id, sample in batch:
            question = sample.get("question")
            if not isinstance(question, str):
                raise TypeError(f"sample {sample_id!r}: question must be a string")
            query_tokens.append(lexical_tokenize(question))

        retrieval_result = index["retriever"].retrieve(
            query_tokens,
            k=top_k_chunks,
            sorted=True,
            return_as="tuple",
            show_progress=False,
        )

        for (sample_id, _), hit_indices, hit_scores in zip(
            batch, retrieval_result.documents, retrieval_result.scores
        ):
            chunk_hits = []
            for chunk_rank, (chunk_index_value, score_value) in enumerate(
                zip(hit_indices, hit_scores), start=1
            ):
                chunk_index = int(chunk_index_value)
                chunk_id, document_id = index["chunk_metadata"][chunk_index]
                chunk = chunks[chunk_index]
                if (
                    str(chunk["chunk_id"]) != chunk_id
                    or str(chunk["document_id"]) != document_id
                ):
                    raise RuntimeError("chunk order does not match the BM25 index")
                chunk_hits.append(
                    {
                        "chunk_id": chunk_id,
                        "document_id": document_id,
                        "score": float(score_value),
                        "chunk_rank": chunk_rank,
                        "text": chunk["text"],
                    }
                )

            aggregated = aggregate_documents(chunk_hits, method="sum_top_2")
            selected_documents = aggregated[:candidate_depth]
            if len(selected_documents) != candidate_depth:
                raise RuntimeError(
                    f"sample {sample_id!r}: expected {candidate_depth} candidates, "
                    f"got {len(selected_documents)}"
                )

            by_document = {document["document_id"]: [] for document in selected_documents}
            for hit in chunk_hits:
                supporting_chunks = by_document.get(hit["document_id"])
                if (
                    supporting_chunks is not None
                    and len(supporting_chunks) < SUPPORTING_CHUNKS_PER_DOCUMENT
                ):
                    supporting_chunks.append(
                        {
                            "chunk_id": hit["chunk_id"],
                            "text": hit["text"],
                            "bm25_rank": hit["chunk_rank"],
                            "bm25_score": hit["score"],
                        }
                    )

            query_candidates = []
            for original_rank, document in enumerate(selected_documents, start=1):
                supporting_chunks = by_document[document["document_id"]]
                if not supporting_chunks:
                    raise RuntimeError("candidate document has no supporting chunk")
                query_candidates.append(
                    {
                        "document_id": document["document_id"],
                        "original_rank": original_rank,
                        "original_score": document["score"],
                        "supporting_chunks": supporting_chunks,
                    }
                )

            candidate_ids = [candidate["document_id"] for candidate in query_candidates]
            if len(candidate_ids) != len(set(candidate_ids)):
                raise RuntimeError(f"sample {sample_id!r}: duplicate candidate IDs")
            candidates_by_query[str(sample_id)] = query_candidates

    return {
        "candidates_by_query": candidates_by_query,
        "reference_rankings": {
            sample_id: [candidate["document_id"] for candidate in candidates]
            for sample_id, candidates in candidates_by_query.items()
        },
        "top_k_chunks": top_k_chunks,
        "candidate_depth": candidate_depth,
        "retrieval_seconds": perf_counter() - started,
    }


def score_query_chunk_pairs(
    reranker: dict,
    pairs: list[tuple[str, str]],
    batch_size: int = 8,
    progress: Callable[[int, int], None] | None = None,
) -> dict:
    """Score query/chunk pairs and report pre-truncation token diagnostics."""

    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")
    if not pairs:
        raise ValueError("pairs must not be empty")

    tokenizer = reranker["tokenizer"]
    model = reranker["model"]
    device = reranker["device"]
    max_sequence_length = reranker["max_sequence_length"]
    scores = []
    token_lengths = []
    model_forward_seconds = 0.0
    scoring_started = perf_counter()

    for batch_start in range(0, len(pairs), batch_size):
        batch = pairs[batch_start : batch_start + batch_size]
        questions = [pair[0] for pair in batch]
        passages = [pair[1] for pair in batch]
        untruncated = tokenizer(
            questions,
            passages,
            padding=False,
            truncation=False,
            return_length=True,
        )
        token_lengths.extend(int(length) for length in untruncated["length"])

        inputs = tokenizer(
            questions,
            passages,
            padding=True,
            truncation="only_second",
            max_length=max_sequence_length,
            return_tensors="pt",
        )
        inputs = {name: value.to(device) for name, value in inputs.items()}

        if device.startswith("cuda"):
            torch.cuda.synchronize()
        forward_started = perf_counter()
        with torch.no_grad():
            logits = model(**inputs, return_dict=True).logits.view(-1).float()
        if device.startswith("cuda"):
            torch.cuda.synchronize()
        model_forward_seconds += perf_counter() - forward_started

        batch_scores = logits.cpu().tolist()
        if len(batch_scores) != len(batch) or not all(
            isfinite(score) for score in batch_scores
        ):
            raise RuntimeError("reranker returned invalid scores")
        scores.extend(float(score) for score in batch_scores)

        completed = min(batch_start + len(batch), len(pairs))
        if progress is not None:
            progress(completed, len(pairs))

    lengths = np.asarray(token_lengths, dtype=np.int32)
    truncated = int(np.sum(lengths > max_sequence_length))
    scoring_seconds = perf_counter() - scoring_started
    return {
        "scores": scores,
        "diagnostics": {
            "number_of_pairs": len(pairs),
            "token_length_before_truncation": {
                "median": float(np.median(lengths)),
                "p95": float(np.percentile(lengths, 95)),
                "max": int(lengths.max()),
            },
            "truncated_pairs": truncated,
            "truncated_fraction": truncated / len(pairs),
            "model_forward_seconds": model_forward_seconds,
            "scoring_seconds": scoring_seconds,
            "model_forward_pairs_per_second": len(pairs) / model_forward_seconds,
            "end_to_end_pairs_per_second": len(pairs) / scoring_seconds,
        },
    }


def rerank_documents(
    candidates: list[dict], supporting_chunk_scores: list[list[float]]
) -> list[dict]:
    """Sum up to two chunk scores and deterministically rerank all candidates."""

    if len(candidates) != len(supporting_chunk_scores):
        raise ValueError("each candidate must have one supporting-score list")

    candidate_ids = [str(candidate["document_id"]) for candidate in candidates]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("candidate document IDs must be unique")

    reranked = []
    for candidate, scores in zip(candidates, supporting_chunk_scores):
        expected_scores = len(candidate["supporting_chunks"])
        if not 1 <= expected_scores <= SUPPORTING_CHUNKS_PER_DOCUMENT:
            raise ValueError("candidate must have one or two supporting chunks")
        if len(scores) != expected_scores:
            raise ValueError("supporting-score count does not match supporting chunks")
        canonical_scores = [float(score) for score in scores]
        if not all(isfinite(score) for score in canonical_scores):
            raise ValueError("cross-encoder scores must be finite")
        reranked.append(
            {
                **candidate,
                "cross_encoder_chunk_scores": canonical_scores,
                "cross_encoder_score": sum(canonical_scores),
            }
        )

    reranked.sort(
        key=lambda document: (
            -document["cross_encoder_score"],
            document["original_rank"],
            str(document["document_id"]),
        )
    )
    if {document["document_id"] for document in reranked} != set(candidate_ids):
        raise RuntimeError("reranking changed the candidate set")
    return reranked


def rerank_fixed_candidates(
    reranker: dict,
    samples: dict,
    candidates_by_query: dict[str, list[dict]],
    batch_size: int = 8,
    progress: Callable[[int, int], None] | None = None,
) -> dict:
    """Score independent query/chunk pairs and rerank each fixed candidate set."""

    pairs = []
    score_counts = []
    for sample_id, sample in samples.items():
        question = sample.get("question")
        if not isinstance(question, str):
            raise TypeError(f"sample {sample_id!r}: question must be a string")
        candidates = candidates_by_query.get(str(sample_id))
        if candidates is None:
            raise KeyError(f"sample {sample_id!r}: missing fixed candidate set")
        query_counts = []
        for candidate in candidates:
            support_count = len(candidate["supporting_chunks"])
            query_counts.append(support_count)
            pairs.extend(
                (question, supporting_chunk["text"])
                for supporting_chunk in candidate["supporting_chunks"]
            )
        score_counts.append((str(sample_id), query_counts))

    scoring = score_query_chunk_pairs(
        reranker,
        pairs,
        batch_size=batch_size,
        progress=progress,
    )
    score_offset = 0
    reranked_by_query = {}
    for sample_id, query_counts in score_counts:
        document_scores = []
        for support_count in query_counts:
            document_scores.append(
                scoring["scores"][score_offset : score_offset + support_count]
            )
            score_offset += support_count
        reranked_by_query[sample_id] = rerank_documents(
            candidates_by_query[sample_id], document_scores
        )
    if score_offset != len(scoring["scores"]):
        raise RuntimeError("not every cross-encoder score was consumed")

    return {
        "reranked_by_query": reranked_by_query,
        "rankings": {
            sample_id: [document["document_id"] for document in documents]
            for sample_id, documents in reranked_by_query.items()
        },
        "diagnostics": scoring["diagnostics"],
    }


def paired_bootstrap(
    reference: list[float],
    alternative: list[float],
    seed: int = 2_026_091_3,
    resamples: int = 10_000,
) -> dict:
    """Bootstrap a paired mean delta over per-query metric contributions."""

    reference_values = np.asarray(reference, dtype=np.float64)
    alternative_values = np.asarray(alternative, dtype=np.float64)
    if reference_values.shape != alternative_values.shape or reference_values.ndim != 1:
        raise ValueError("reference and alternative must be same-length vectors")
    if reference_values.size == 0:
        raise ValueError("metric contributions must not be empty")
    if resamples <= 0:
        raise ValueError("resamples must be greater than zero")

    paired_deltas = alternative_values - reference_values
    generator = np.random.default_rng(seed)
    bootstrap_deltas = np.empty(resamples, dtype=np.float64)
    for resample_index in range(resamples):
        indices = generator.integers(0, paired_deltas.size, paired_deltas.size)
        bootstrap_deltas[resample_index] = paired_deltas[indices].mean()

    return {
        "observed_delta": float(paired_deltas.mean()),
        "bootstrap_mean": float(bootstrap_deltas.mean()),
        "percentile_interval_95": [
            float(np.percentile(bootstrap_deltas, 2.5)),
            float(np.percentile(bootstrap_deltas, 97.5)),
        ],
        "fraction_delta_greater_than_zero": float(np.mean(bootstrap_deltas > 0)),
        "seed": seed,
        "resamples": resamples,
    }


def _validate_split(source_path: Path, manifest_path: Path) -> tuple[dict, dict]:
    samples = load_legal_ir(source_path)
    with manifest_path.open(encoding="utf-8") as stream:
        manifest = json.load(stream)
    source_digest = sha256(source_path.read_bytes()).hexdigest()
    if source_digest != manifest["source_sha256"]:
        raise RuntimeError("LegalIR source SHA-256 does not match the split manifest")
    recomputed = make_legalir_split(samples)
    for split_name in ("train", "dev", "holdout"):
        if recomputed[split_name] != manifest[f"{split_name}_ids"]:
            raise RuntimeError(f"{split_name} IDs do not reproduce from current source")
    all_ids = [sample_id for ids in recomputed.values() for sample_id in ids]
    if len(all_ids) != len(set(all_ids)) or set(all_ids) != set(samples):
        raise RuntimeError("split IDs are not a unique, complete source partition")
    return select_samples(samples, manifest["dev_ids"]), {
        "source_sha256": source_digest,
        "source_queries": len(samples),
        "dev_queries": len(manifest["dev_ids"]),
        "manifest_reproduced": True,
        "complete_unique_partition": True,
    }


def _load_bundled_scorer(repository: Path):
    scorer_path = repository / "scoring" / "LegalIR" / "scoring.py"
    spec = importlib.util.spec_from_file_location("bundled_legalir_scorer", scorer_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load bundled scorer from {scorer_path}")
    scorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scorer)
    return scorer


def _bundled_contributions(scorer, predictions: dict, truth: dict) -> dict:
    contributions = {"precision": [], "recall": []}
    for sample_id, answer in truth.items():
        scores = scorer.eval_retrieval(
            {sample_id: predictions[sample_id]},
            {sample_id: answer},
        )
        for metric, values in contributions.items():
            values.append(float(scores[metric]))
    return contributions


def run_dev_experiment(
    repository: str | Path,
    batch_size: int = 8,
    smoke_queries: int = 2,
    model_path: str | Path | None = None,
    legalir_source_path: str | Path | None = None,
    corpus_path: str | Path | None = None,
    manifest_path: str | Path | None = None,
) -> dict:
    """Run one smoke check followed by the fixed full-DEV reranking experiment."""

    repository = Path(repository).resolve()
    if not 1 <= smoke_queries <= 3:
        raise ValueError("smoke_queries must be between one and three")

    dev_samples, split_check = _validate_split(
        Path(legalir_source_path)
        if legalir_source_path is not None
        else repository / "data" / "LegalIR" / "train.json",
        Path(manifest_path)
        if manifest_path is not None
        else repository / "configs" / "legalir_split_v1.json",
    )
    documents = load_corpus(
        Path(corpus_path)
        if corpus_path is not None
        else repository / "data" / "LegalIR" / "selected-contexts"
    )
    chunks = chunk_corpus(documents, chunk_size=2_000, overlap=200)
    if len(documents) != 8_532 or len(chunks) != 199_816:
        raise RuntimeError("current corpus does not match the fixed reference")
    index = build_bm25(chunks, k1=1.5, b=0.75)
    if index["library_version"] != "0.3.11" or index["method"] != "lucene":
        raise RuntimeError("BM25 implementation does not match fixed controls")

    reranker = load_reranker(model_path=model_path)
    smoke_samples = dict(list(dev_samples.items())[:smoke_queries])
    smoke_candidates = build_fixed_candidates(index, chunks, smoke_samples)
    smoke_result = rerank_fixed_candidates(
        reranker,
        smoke_samples,
        smoke_candidates["candidates_by_query"],
        batch_size=batch_size,
    )
    smoke_sets_preserved = all(
        set(smoke_candidates["reference_rankings"][sample_id])
        == set(smoke_result["rankings"][sample_id])
        for sample_id in smoke_samples
    )
    # Re-sort the already scored candidates to check ordering without another model call.
    deterministic_smoke = True
    for sample_id in smoke_samples:
        scored_by_id = {
            document["document_id"]: document
            for document in smoke_result["reranked_by_query"][sample_id]
        }
        original_candidates = smoke_candidates["candidates_by_query"][sample_id]
        score_lists = [
            scored_by_id[candidate["document_id"]]["cross_encoder_chunk_scores"]
            for candidate in original_candidates
        ]
        repeated = rerank_documents(original_candidates, score_lists)
        deterministic_smoke &= [item["document_id"] for item in repeated] == smoke_result[
            "rankings"
        ][sample_id]
    if not smoke_sets_preserved or not deterministic_smoke:
        raise RuntimeError("smoke test failed candidate preservation or determinism")

    fixed_candidates = build_fixed_candidates(index, chunks, dev_samples)
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()

    last_progress_time = [perf_counter()]

    def show_progress(completed: int, total: int) -> None:
        now = perf_counter()
        if completed == total or now - last_progress_time[0] >= 30:
            print(f"reranking pairs: {completed}/{total}", flush=True)
            last_progress_time[0] = now

    reranked = rerank_fixed_candidates(
        reranker,
        dev_samples,
        fixed_candidates["candidates_by_query"],
        batch_size=batch_size,
        progress=show_progress,
    )

    reference_rankings = fixed_candidates["reference_rankings"]
    alternative_rankings = reranked["rankings"]
    candidate_sets_identical = sum(
        set(reference_rankings[sample_id]) == set(alternative_rankings[sample_id])
        for sample_id in dev_samples
    )
    if candidate_sets_identical != len(dev_samples):
        raise RuntimeError("reranking changed at least one fixed candidate set")

    depths = (5, 10, 20, 50, 100)
    reference_internal = evaluate_retrieval(
        dev_samples, reference_rankings, candidate_depths=depths
    )
    alternative_internal = evaluate_retrieval(
        dev_samples, alternative_rankings, candidate_depths=depths
    )
    reference_ceiling = reference_internal["candidate_recall"][100]
    alternative_ceiling = alternative_internal["candidate_recall"][100]
    if reference_ceiling != alternative_ceiling:
        raise RuntimeError("candidate Recall@100 changed after reranking")

    scorer = _load_bundled_scorer(repository)
    truth = {
        sample_id: sample["answer"] for sample_id, sample in dev_samples.items()
    }
    reference_predictions = make_legalir_predictions(reference_rankings)
    alternative_predictions = make_legalir_predictions(alternative_rankings)
    reference_bundled = {
        metric: float(value)
        for metric, value in scorer.eval_retrieval(
            reference_predictions, truth
        ).items()
    }
    alternative_bundled = {
        metric: float(value)
        for metric, value in scorer.eval_retrieval(
            alternative_predictions, truth
        ).items()
    }

    deltas = {
        "bundled_precision": alternative_bundled["precision"]
        - reference_bundled["precision"],
        "bundled_recall": alternative_bundled["recall"]
        - reference_bundled["recall"],
        "mrr": alternative_internal["mrr"] - reference_internal["mrr"],
    }
    for depth in (10, 20, 50):
        deltas[f"recall_at_{depth}"] = (
            alternative_internal["candidate_recall"][depth]["mean"]
            - reference_internal["candidate_recall"][depth]["mean"]
        )

    bootstrap = None
    if deltas["bundled_precision"] > 0 and deltas["bundled_recall"] > 0:
        reference_contributions = _bundled_contributions(
            scorer, reference_predictions, truth
        )
        alternative_contributions = _bundled_contributions(
            scorer, alternative_predictions, truth
        )
        bootstrap = {
            metric: paired_bootstrap(
                reference_contributions[metric], alternative_contributions[metric]
            )
            for metric in ("precision", "recall")
        }

    runtime = {
        "model_load_seconds": reranker["load_seconds"],
        "candidate_retrieval_seconds": fixed_candidates["retrieval_seconds"],
        **reranked["diagnostics"],
        "peak_gpu_memory_bytes": (
            int(torch.cuda.max_memory_allocated()) if torch.cuda.is_available() else None
        ),
    }
    return {
        "split_check": split_check,
        "controls": {
            "documents": len(documents),
            "chunks": len(chunks),
            "chunk_size": 2_000,
            "overlap": 200,
            "bm25_library": f"bm25s=={bm25s.__version__}",
            "bm25_method": "lucene",
            "k1": 1.5,
            "b": 0.75,
            "top_k_chunks": TOP_K_CHUNKS,
            "aggregation": "sum top-2",
            "candidate_depth": CANDIDATE_DEPTH,
        },
        "reranker": {
            "model": reranker["model_name"],
            "requested_revision": reranker["requested_revision"],
            "resolved_revision": reranker["resolved_revision"],
            "tokenizer": reranker["tokenizer"].name_or_path,
            "max_sequence_length": reranker["max_sequence_length"],
            "torch_version": torch.__version__,
            "transformers_version": transformers.__version__,
            "device": reranker["device"],
            "dtype": reranker["dtype"],
            "batch_size": batch_size,
        },
        "smoke_test": {
            "queries": smoke_queries,
            "score_shape": [smoke_result["diagnostics"]["number_of_pairs"]],
            "finite_scores": True,
            "candidate_sets_preserved": smoke_sets_preserved,
            "deterministic_ordering": deterministic_smoke,
        },
        "candidate_sets_identical": {
            "queries": candidate_sets_identical,
            "total_queries": len(dev_samples),
        },
        "candidate_recall_at_100_ceiling": reference_ceiling,
        "reference": {
            "bundled_scorer": reference_bundled,
            "internal": reference_internal,
            "first_gold_rank": summarize_first_gold_ranks(
                dev_samples, reference_rankings
            ),
        },
        "reranked": {
            "bundled_scorer": alternative_bundled,
            "internal": alternative_internal,
            "first_gold_rank": summarize_first_gold_ranks(
                dev_samples, alternative_rankings
            ),
        },
        "deltas": deltas,
        "paired_top_5": compare_official_style_top_5(
            dev_samples, reference_rankings, alternative_rankings
        ),
        "paired_bootstrap": bootstrap,
        "runtime": runtime,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run fixed-candidate zero-shot cross-encoder reranking on DEV"
    )
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--smoke-queries", type=int, default=2)
    parser.add_argument("--model-path", type=Path)
    parser.add_argument("--legalir-source-path", type=Path)
    parser.add_argument("--corpus-path", type=Path)
    parser.add_argument("--manifest-path", type=Path)
    arguments = parser.parse_args()
    result = run_dev_experiment(
        arguments.repository,
        batch_size=arguments.batch_size,
        smoke_queries=arguments.smoke_queries,
        model_path=arguments.model_path,
        legalir_source_path=arguments.legalir_source_path,
        corpus_path=arguments.corpus_path,
        manifest_path=arguments.manifest_path,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
