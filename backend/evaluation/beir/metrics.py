from __future__ import annotations

import math


def _ranked_ids(results: dict[str, float]) -> list[str]:
    return [item[0] for item in sorted(results.items(), key=lambda item: (-item[1], item[0]))]


def _local_metrics(
    qrels: dict[str, dict[str, int]],
    results: dict[str, dict[str, float]],
) -> dict[str, float]:
    totals = {
        "Recall@5": 0.0,
        "Recall@10": 0.0,
        "MRR@10": 0.0,
        "nDCG@10": 0.0,
        "Precision@10": 0.0,
        "MAP@10": 0.0,
    }
    if not qrels:
        return totals

    for query_id, judgments in qrels.items():
        relevant = {corpus_id for corpus_id, score in judgments.items() if score > 0}
        ranked = _ranked_ids(results.get(query_id, {}))
        for cutoff in (5, 10):
            hits = sum(corpus_id in relevant for corpus_id in ranked[:cutoff])
            totals[f"Recall@{cutoff}"] += hits / len(relevant) if relevant else 0.0

        top_ten = ranked[:10]
        relevant_ranks = [rank for rank, corpus_id in enumerate(top_ten, 1) if corpus_id in relevant]
        totals["MRR@10"] += 1.0 / relevant_ranks[0] if relevant_ranks else 0.0
        totals["Precision@10"] += len(relevant_ranks) / 10

        precision_sum = 0.0
        hits = 0
        for rank, corpus_id in enumerate(top_ten, 1):
            if corpus_id in relevant:
                hits += 1
                precision_sum += hits / rank
        totals["MAP@10"] += precision_sum / min(len(relevant), 10) if relevant else 0.0

        dcg = sum(
            judgments.get(corpus_id, 0) / math.log2(rank + 1)
            for rank, corpus_id in enumerate(top_ten, 1)
        )
        ideal = sorted((score for score in judgments.values() if score > 0), reverse=True)[:10]
        idcg = sum(score / math.log2(rank + 1) for rank, score in enumerate(ideal, 1))
        totals["nDCG@10"] += dcg / idcg if idcg else 0.0

    return {name: value / len(qrels) for name, value in totals.items()}


def evaluate_beir(
    qrels: dict[str, dict[str, int]],
    results: dict[str, dict[str, float]],
) -> tuple[dict[str, float], str]:
    try:
        from beir.retrieval.evaluation import EvaluateRetrieval
    except ImportError:
        return _local_metrics(qrels, results), "local-compatible"

    ndcg, mean_ap, recall, precision = EvaluateRetrieval.evaluate(qrels, results, [5, 10])
    mrr = EvaluateRetrieval.evaluate_custom(qrels, results, [10], metric="mrr")
    return (
        {
            "Recall@5": recall["Recall@5"],
            "Recall@10": recall["Recall@10"],
            "MRR@10": mrr["MRR@10"],
            "nDCG@10": ndcg["NDCG@10"],
            "Precision@10": precision["P@10"],
            "MAP@10": mean_ap["MAP@10"],
        },
        "beir",
    )
