from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import json
import math
from pathlib import Path
from statistics import median
from time import perf_counter

import chromadb

from app.core.config import settings
from app.services.document.embedding_service import EmbeddingService
from app.services.rag.retrieval_service import (
    CANDIDATE_MULTIPLIER,
    MAX_CONTEXT_CHUNKS,
    MAX_RERANK_CANDIDATES,
    MAX_RETRIEVAL_QUERIES,
    RERANKER_MODEL,
    RRF_K,
    RetrievalService,
)
from evaluation.beir.common import (
    BEIR_DATA_ROOT,
    BEIR_RESULTS_ROOT,
    OfflineRedis,
    collection_name,
    git_commit,
    manifest_path,
    write_json_once,
)
from evaluation.beir.loader import BeirDataset
from evaluation.beir.metrics import evaluate_beir
from evaluation.beir.ranking import collapse_chunk_rankings

TOP_K = 8


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


async def run_benchmark(
    *,
    dataset: str,
    split: str,
    experiment: str,
    dataset_root: Path,
    chroma_path: Path,
) -> Path:
    manifest_file = manifest_path(dataset)
    if not manifest_file.is_file():
        raise FileNotFoundError("Benchmark index manifest missing; run the prepare command first.")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if Path(manifest["chroma_path"]).resolve() != chroma_path.resolve():
        raise ValueError("The requested Chroma path does not match the prepared index manifest.")

    beir_dataset = BeirDataset(dataset_root, split=split)
    queries = {query.query_id: query.text for query in beir_dataset.load_queries()}
    qrels = beir_dataset.load_qrels()

    client = chromadb.PersistentClient(path=str(chroma_path))
    collection = client.get_collection(collection_name(dataset))
    stored = collection.get(include=["metadatas"])
    metadatas = stored.get("metadatas") or []
    document_ids = [int(metadata["document_id"]) for metadata in metadatas]
    document_titles = {
        int(metadata["document_id"]): str(metadata.get("document_title") or "")
        for metadata in metadatas
    }

    retrieval = RetrievalService(
        chroma_client=client,
        embedding_service=EmbeddingService(),
        redis=OfflineRedis(),
        collection_name=collection_name(dataset),
    )
    rankings: dict[str, dict[str, float]] = {}
    latencies_ms = []
    for query_id in qrels:
        query = queries.get(query_id)
        if query is None:
            raise KeyError(f"Missing query text for qrels query '{query_id}'")
        started = perf_counter()
        chunks = await retrieval.hybrid_search(
            query=query,
            user_id=0,
            document_ids=document_ids,
            document_titles=document_titles,
            top_k=TOP_K,
            trace=None,
        )
        latencies_ms.append((perf_counter() - started) * 1000)
        rankings[query_id] = collapse_chunk_rankings(chunks)

    metrics, metric_backend = evaluate_beir(qrels, rankings)
    payload = {
        "metadata": {
            "benchmark": "BEIR",
            "dataset": dataset,
            "split": split,
            "experiment": experiment,
            "timestamp": datetime.now(UTC).isoformat(),
            "git_commit": git_commit(),
            "embedding_model": settings.VOYAGE_MODEL,
            "reranker_model": RERANKER_MODEL,
            "top_k": TOP_K,
            "candidate_multiplier": CANDIDATE_MULTIPLIER,
            "rrf_k": RRF_K,
            "max_retrieval_queries": MAX_RETRIEVAL_QUERIES,
            "max_rerank_candidates": MAX_RERANK_CANDIDATES,
            "max_context_chunks": MAX_CONTEXT_CHUNKS,
            "collection": collection_name(dataset),
            "metric_backend": metric_backend,
        },
        "metrics": metrics,
        "latency": {
            "total_queries": len(latencies_ms),
            "median_retrieval_ms": median(latencies_ms) if latencies_ms else 0.0,
            "p95_retrieval_ms": _percentile(latencies_ms, 0.95),
        },
        "rankings": rankings,
    }
    return write_json_once(BEIR_RESULTS_ROOT / dataset, experiment, payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run retrieval-only evaluation on BEIR")
    parser.add_argument("--dataset", default="scifact")
    parser.add_argument("--split", default="test")
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--chroma-path", type=Path, default=Path(settings.CHROMA_PERSIST_DIR))
    args = parser.parse_args()
    dataset_root = args.data_root or BEIR_DATA_ROOT / args.dataset
    result_path = asyncio.run(
        run_benchmark(
            dataset=args.dataset,
            split=args.split,
            experiment=args.experiment,
            dataset_root=dataset_root,
            chroma_path=args.chroma_path,
        )
    )
    print(f"Results written to {result_path}")


if __name__ == "__main__":
    main()
