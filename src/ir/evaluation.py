"""Local document-ranking diagnostics for LegalIR experiments."""


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
