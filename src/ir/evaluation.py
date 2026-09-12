"""Local document-ranking diagnostics for LegalIR experiments."""

from collections import Counter
from statistics import median


def _percentile(values: list[int], percent: int) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percent / 100
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return float(ordered[lower] + (ordered[upper] - ordered[lower]) * fraction)


def evaluate_retrieval(
    samples: dict,
    rankings: dict[str, list[str]],
    candidate_depths: tuple[int, ...] = (10, 20, 50, 100, 200),
) -> dict:
    """Evaluate candidate recall and official-style top-5 set-overlap scores."""

    recall_values = {depth: [] for depth in candidate_depths}
    reciprocal_ranks = []
    top_5_precision = []
    top_5_recall = []
    zero_recall_at_100_ids = []
    full_recall_at_100 = 0
    gold_only_after_rank_5 = 0

    for sample_id, sample in samples.items():
        gold_values = sample.get("answer")
        if not isinstance(gold_values, list) or not gold_values:
            raise ValueError(f"sample {sample_id!r}: expected a non-empty answer list")

        gold = {str(document_id) for document_id in gold_values}
        ranked = [str(document_id) for document_id in rankings.get(str(sample_id), [])]
        if len(ranked) != len(set(ranked)):
            raise ValueError(f"sample {sample_id!r}: ranking contains duplicate IDs")

        for depth in candidate_depths:
            recall_values[depth].append(len(gold.intersection(ranked[:depth])) / len(gold))

        first_gold_rank = next(
            (rank for rank, document_id in enumerate(ranked, start=1) if document_id in gold),
            None,
        )
        reciprocal_ranks.append(0.0 if first_gold_rank is None else 1 / first_gold_rank)
        if first_gold_rank is not None and first_gold_rank > 5:
            gold_only_after_rank_5 += 1

        top_5 = ranked[:5]
        overlap = len(gold.intersection(top_5))
        top_5_precision.append(overlap / len(top_5) if 0 < len(top_5) <= 5 else 0.0)
        top_5_recall.append(overlap / len(gold) if 0 < len(top_5) <= 5 else 0.0)

        recall_at_100 = len(gold.intersection(ranked[:100])) / len(gold)
        if recall_at_100 == 0:
            zero_recall_at_100_ids.append(str(sample_id))
        if recall_at_100 == 1:
            full_recall_at_100 += 1

    number_of_queries = len(samples)
    if number_of_queries == 0:
        raise ValueError("samples must not be empty")

    candidate_recall = {}
    for depth, values in recall_values.items():
        candidate_recall[depth] = {
            "mean": sum(values) / number_of_queries,
            "zero_recall_rate": sum(value == 0 for value in values)
            / number_of_queries,
            "full_recall_rate": sum(value == 1 for value in values)
            / number_of_queries,
        }

    return {
        "number_of_queries": number_of_queries,
        "candidate_recall": candidate_recall,
        "mrr": sum(reciprocal_ranks) / number_of_queries,
        "official_style_top_5": {
            "precision": sum(top_5_precision) / number_of_queries,
            "recall": sum(top_5_recall) / number_of_queries,
        },
        "queries_with_zero_recall_at_100": len(zero_recall_at_100_ids),
        "queries_with_full_recall_at_100": full_recall_at_100,
        "queries_where_gold_appears_only_after_rank_5": gold_only_after_rank_5,
        "zero_recall_at_100_sample_ids": zero_recall_at_100_ids[:20],
    }


def diagnose_dev_rankings(
    samples: dict, rankings: dict[str, list[str]], max_examples: int = 20
) -> dict:
    """Separate dev coverage failures from deep-ranking failures at depth 200."""

    if not samples:
        raise ValueError("samples must not be empty")
    if max_examples < 0:
        raise ValueError("max_examples must be non-negative")

    coverage_examples = []
    ranking_examples = []
    first_gold_ranks = []
    rank_bins = Counter()
    all_gold_within = {depth: 0 for depth in (5, 10, 20, 50, 100, 200)}

    for sample_id, sample in samples.items():
        gold_values = sample.get("answer")
        if not isinstance(gold_values, list) or not gold_values:
            raise ValueError(f"sample {sample_id!r}: expected a non-empty answer list")

        gold_document_ids = list(dict.fromkeys(str(value) for value in gold_values))
        gold = set(gold_document_ids)
        ranked = [str(value) for value in rankings.get(str(sample_id), [])[:200]]
        if len(ranked) != len(set(ranked)):
            raise ValueError(f"sample {sample_id!r}: ranking contains duplicate IDs")

        gold_ranks = [
            rank
            for rank, document_id in enumerate(ranked, start=1)
            if document_id in gold
        ]
        first_gold_rank = gold_ranks[0] if gold_ranks else None
        example = {
            "sample_id": str(sample_id),
            "question": sample.get("question"),
            "gold_document_ids": gold_document_ids,
            "first_gold_rank": first_gold_rank,
            "gold_ranks_within_top_200": gold_ranks,
            "gold_count": len(gold),
        }

        if first_gold_rank is None:
            rank_bins["not_found"] += 1
            if len(coverage_examples) < max_examples:
                coverage_examples.append(example)
        else:
            first_gold_ranks.append(first_gold_rank)
            if first_gold_rank == 1:
                rank_bins["1"] += 1
            elif first_gold_rank <= 5:
                rank_bins["2-5"] += 1
            elif first_gold_rank <= 10:
                rank_bins["6-10"] += 1
            elif first_gold_rank <= 20:
                rank_bins["11-20"] += 1
            elif first_gold_rank <= 50:
                rank_bins["21-50"] += 1
            elif first_gold_rank <= 100:
                rank_bins["51-100"] += 1
            else:
                rank_bins["101-200"] += 1

            if first_gold_rank > 5 and len(ranking_examples) < max_examples:
                ranking_examples.append(example)

        for depth in all_gold_within:
            if gold.issubset(ranked[:depth]):
                all_gold_within[depth] += 1

    number_of_queries = len(samples)
    coverage_count = rank_bins["not_found"]
    ranking_count = sum(
        rank_bins[label]
        for label in ("6-10", "11-20", "21-50", "51-100", "101-200")
    )
    ordered_bin_labels = (
        "1",
        "2-5",
        "6-10",
        "11-20",
        "21-50",
        "51-100",
        "101-200",
        "not_found",
    )

    return {
        "number_of_queries": number_of_queries,
        "coverage_failures": {
            "count": coverage_count,
            "fraction": coverage_count / number_of_queries,
            "examples": coverage_examples,
        },
        "ranking_failures": {
            "count": ranking_count,
            "fraction": ranking_count / number_of_queries,
            "examples": ranking_examples,
        },
        "first_gold_rank_distribution_when_found": {
            "median": float(median(first_gold_ranks)) if first_gold_ranks else None,
            "p90": _percentile(first_gold_ranks, 90),
            "p95": _percentile(first_gold_ranks, 95),
            "max": max(first_gold_ranks, default=None),
        },
        "first_gold_rank_counts": {
            label: rank_bins[label] for label in ordered_bin_labels
        },
        "all_gold_within_depth_fraction": {
            depth: count / number_of_queries
            for depth, count in all_gold_within.items()
        },
    }
