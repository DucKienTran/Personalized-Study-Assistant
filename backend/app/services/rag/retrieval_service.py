# app/services/ai/retrieval_service.py
import asyncio
import json
import logging
import re
from time import perf_counter
from typing import Any, Dict, List, Tuple

from chromadb.api import ClientAPI
from flashrank import Ranker, RerankRequest
from flashrank.Config import default_model as FLASHRANK_DEFAULT_MODEL
from rank_bm25 import BM25Okapi
from redis.asyncio import Redis

from app.core.config import settings
from app.services.document.embedding_service import EmbeddingService
from app.services.rag.evaluation_trace import EvaluationTrace
from app.services.rag.retrieval_models import RetrievalResult

logger = logging.getLogger(__name__)

_global_ranker: Ranker | None = None
CANDIDATE_MULTIPLIER = 4
RRF_K = 60
RERANKER_MODEL = FLASHRANK_DEFAULT_MODEL


def _get_global_ranker() -> Ranker:
    global _global_ranker
    if _global_ranker is None:
        _global_ranker = Ranker(model_name=RERANKER_MODEL)
    return _global_ranker


def _tokenize_text(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())


class RetrievalService:
    def __init__(
        self,
        chroma_client: ClientAPI,
        embedding_service: EmbeddingService,
        redis: Redis,
    ):
        self.chroma_client = chroma_client
        self.embedding_service = embedding_service
        self.redis = redis
        self.chroma_collection = self.chroma_client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME
        )
        self.ranker = _get_global_ranker()
        self._bm25_cache: Dict[Tuple[int, str], Dict[str, Any]] = {}

    def _vector_search_sync(
        self,
        query: str,
        document_ids: list[int],
        top_k: int = 10,
        trace: EvaluationTrace | None = None,
    ) -> List[RetrievalResult]:
        embedding_started = perf_counter()
        query_embedding = self.embedding_service.generate_query_embedding(query)
        if trace:
            trace.set_timing("query_embedding", (perf_counter() - embedding_started) * 1000)

        search_started = perf_counter()
        results = self.chroma_collection.query(
            query_embeddings=[query_embedding],
            where={"document_id": {"$in": document_ids}},
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        if trace:
            trace.set_timing("vector_search", (perf_counter() - search_started) * 1000)

        retrieval_results = []
        if not results or not results["ids"] or not results["ids"][0]:
            if trace:
                trace.set_retrieval_stage("vector_candidates", [])
            return retrieval_results

        trace_candidates = [] if trace else None
        for rank, (chunk_id, text, meta, dist) in enumerate(
            zip(
                results["ids"][0],
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ),
            start=1,
        ):
            score = 1.0 - float(dist) if dist is not None else None
            if trace_candidates is not None:
                trace_candidates.append(
                    {
                        "chunk_id": chunk_id,
                        "document_id": int(meta.get("document_id", 0)),
                        "rank": rank,
                        "score": score,
                        "distance": float(dist) if dist is not None else None,
                    }
                )

            retrieval_results.append(
                RetrievalResult(
                    chunk_id=chunk_id,
                    document_id=int(meta.get("document_id", 0)),
                    text=text,
                    vector_score=score,
                    page_start=int(meta.get("page_start", 0)),
                    page_end=int(meta.get("page_end", 0)),
                    header_path=meta.get("header_path", []),
                )
            )
        if trace and trace_candidates is not None:
            trace.set_retrieval_stage("vector_candidates", trace_candidates)
        return retrieval_results

    async def vector_search(
        self,
        query: str,
        document_ids: list[int],
        top_k: int = 10,
        trace: EvaluationTrace | None = None,
    ) -> List[RetrievalResult]:
        return await asyncio.to_thread(self._vector_search_sync, query, document_ids, top_k, trace)

    async def _get_or_fetch_corpus(
        self, user_id: int, document_ids: list[int], version: str
    ) -> list[dict]:
        doc_key = ",".join(map(str, sorted(list(set(document_ids)))))
        cache_key = f"rag:bm25:corpus:{user_id}:{doc_key}:{version}"

        cached_data = await self.redis.get(cache_key)
        if cached_data:
            logger.debug(f"bm25 redis corpus cache hit for user_id={user_id} docs={doc_key}")
            return json.loads(cached_data)

        logger.info(
            f"bm25 redis corpus cache miss for user_id={user_id} docs={doc_key}, fetching from chromadb"
        )
        all_data = self.chroma_collection.get(
            where={"document_id": {"$in": document_ids}},
            include=["documents", "metadatas"],
        )

        if not all_data or not all_data["documents"]:
            return []

        chunks_to_cache = []
        for cid, doc, meta in zip(all_data["ids"], all_data["documents"], all_data["metadatas"]):
            chunks_to_cache.append(
                {
                    "chunk_id": cid,
                    "document_id": int(meta.get("document_id", 0)),
                    "text": doc,
                    "page_start": int(meta.get("page_start") or 0),
                    "page_end": int(meta.get("page_end") or 0),
                    "header_path": meta.get("header_path", []),
                    "tokens": _tokenize_text(doc),
                }
            )

        if chunks_to_cache:
            await self.redis.set(cache_key, json.dumps(chunks_to_cache), ex=86400)

        return chunks_to_cache

    async def _get_or_build_bm25(
        self, user_id: int, document_ids: list[int]
    ) -> tuple[BM25Okapi | None, list[dict]]:
        current_version = await self.redis.get(f"rag:bm25:version:{user_id}") or "0"
        doc_key = ",".join(map(str, sorted(list(set(document_ids)))))
        cache_key = (user_id, doc_key)

        cached = self._bm25_cache.get(cache_key)

        if cached and cached.get("version") == current_version:
            logger.debug(f"bm25 ram index hit for user_id={user_id} docs={doc_key}")
            return cached["bm25"], cached["chunks"]

        logger.info(
            f"building bm25 ram index for user_id={user_id} docs={doc_key}, version={current_version}"
        )
        corpus_chunks = await self._get_or_fetch_corpus(user_id, document_ids, current_version)
        if not corpus_chunks:
            return None, []

        tokenized_corpus = [chunk["tokens"] for chunk in corpus_chunks]
        bm25 = BM25Okapi(tokenized_corpus)

        self._bm25_cache[cache_key] = {
            "version": current_version,
            "bm25": bm25,
            "chunks": corpus_chunks,
        }
        return bm25, corpus_chunks

    def _bm25_search_sync(
        self,
        query: str,
        bm25: BM25Okapi,
        corpus_chunks: list[dict],
        top_k: int = 10,
    ) -> List[RetrievalResult]:
        if not bm25 or not corpus_chunks:
            return []

        tokenized_query = _tokenize_text(query)
        scores = bm25.get_scores(tokenized_query)

        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True,
        )[:top_k]

        retrieval_results: List[RetrievalResult] = []

        for idx in top_indices:
            score = float(scores[idx])
            if score <= 0:
                continue

            item = corpus_chunks[idx]
            retrieval_results.append(
                RetrievalResult(
                    chunk_id=item["chunk_id"],
                    document_id=item["document_id"],
                    text=item["text"],
                    bm25_score=score,
                    page_start=item["page_start"],
                    page_end=item["page_end"],
                    header_path=item["header_path"],
                )
            )

        return retrieval_results

    async def bm25_search(
        self,
        query: str,
        user_id: int,
        document_ids: list[int],
        top_k: int = 10,
        trace: EvaluationTrace | None = None,
    ) -> List[RetrievalResult]:
        load_started = perf_counter()
        bm25, corpus_chunks = await self._get_or_build_bm25(user_id, document_ids)
        if trace:
            trace.set_timing("bm25_load", (perf_counter() - load_started) * 1000)
        if not bm25:
            if trace:
                trace.set_retrieval_stage("bm25_candidates", [])
            return []

        search_started = perf_counter()
        results = await asyncio.to_thread(self._bm25_search_sync, query, bm25, corpus_chunks, top_k)
        if trace:
            trace.set_timing("bm25_search", (perf_counter() - search_started) * 1000)
            trace.set_retrieval_stage(
                "bm25_candidates",
                [
                    {
                        "chunk_id": result.chunk_id,
                        "document_id": result.document_id,
                        "rank": rank,
                        "score": result.bm25_score,
                    }
                    for rank, result in enumerate(results, start=1)
                ],
            )
        return results

    def reciprocal_rank_fusion(
        self,
        vector_results: List[RetrievalResult],
        bm25_results: List[RetrievalResult],
        k: int = RRF_K,
        top_k: int = 10,
        trace: EvaluationTrace | None = None,
    ) -> List[RetrievalResult]:
        rrf_scores: dict[str, float] = {}
        items_map: dict[str, RetrievalResult] = {}

        for rank, res in enumerate(vector_results, start=1):
            rrf_scores[res.chunk_id] = rrf_scores.get(res.chunk_id, 0.0) + (1.0 / (k + rank))
            items_map[res.chunk_id] = res

        for rank, res in enumerate(bm25_results, start=1):
            rrf_scores[res.chunk_id] = rrf_scores.get(res.chunk_id, 0.0) + (1.0 / (k + rank))
            if res.chunk_id in items_map:
                items_map[res.chunk_id].bm25_score = res.bm25_score
            else:
                items_map[res.chunk_id] = res

        sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)

        results = []
        vector_ranks = (
            {result.chunk_id: rank for rank, result in enumerate(vector_results, 1)}
            if trace
            else {}
        )
        bm25_ranks = (
            {result.chunk_id: rank for rank, result in enumerate(bm25_results, 1)} if trace else {}
        )
        trace_candidates = [] if trace else None
        for rank, cid in enumerate(sorted_chunk_ids[:top_k], start=1):
            item = items_map[cid]
            item.retrieval_score = rrf_scores[cid]
            results.append(item)
            if trace_candidates is not None:
                trace_candidates.append(
                    {
                        "chunk_id": cid,
                        "document_id": item.document_id,
                        "rank": rank,
                        "score": rrf_scores[cid],
                        "vector_rank": vector_ranks.get(cid),
                        "bm25_rank": bm25_ranks.get(cid),
                    }
                )
        if trace and trace_candidates is not None:
            trace.set_retrieval_stage("rrf_candidates", trace_candidates)
        return results

    def rerank(
        self,
        query: str,
        candidates: List[RetrievalResult],
        top_k: int = 5,
        trace: EvaluationTrace | None = None,
    ) -> List[RetrievalResult]:
        if not candidates:
            if trace:
                trace.set_reranker(inputs=[], outputs=[], fallback=False)
            return []

        trace_inputs = (
            [
                {
                    "chunk_id": result.chunk_id,
                    "document_id": result.document_id,
                    "input_rank": rank,
                }
                for rank, result in enumerate(candidates, start=1)
            ]
            if trace
            else []
        )
        input_ranks = {candidate["chunk_id"]: candidate["input_rank"] for candidate in trace_inputs}
        try:
            candidate_map = {res.chunk_id: res for res in candidates}
            passages = [{"id": res.chunk_id, "text": res.text} for res in candidates]

            rerank_request = RerankRequest(query=query, passages=passages)
            results = self.ranker.rerank(rerank_request)  # already sorted best-first

            reranked_results = []
            trace_outputs = [] if trace else None
            for rank, item in enumerate(results[:top_k], start=1):
                chunk_id = item.get("id")
                if chunk_id in candidate_map:
                    res = candidate_map[chunk_id]
                    res.rerank_score = item.get("score")
                    res.rank = rank
                    reranked_results.append(res)
                    if trace_outputs is not None:
                        trace_outputs.append(
                            {
                                "chunk_id": chunk_id,
                                "document_id": res.document_id,
                                "input_rank": input_ranks[chunk_id],
                                "output_rank": rank,
                                "score": (
                                    float(res.rerank_score)
                                    if res.rerank_score is not None
                                    else None
                                ),
                            }
                        )

            if trace and trace_outputs is not None:
                trace.set_reranker(inputs=trace_inputs, outputs=trace_outputs, fallback=False)
            return reranked_results
        except Exception:
            logger.exception("flashrank rerank failed, fallback to candidate order")
            fallback_results = candidates[:top_k]
            if trace:
                trace.set_reranker(
                    inputs=trace_inputs,
                    outputs=[
                        {
                            "chunk_id": result.chunk_id,
                            "document_id": result.document_id,
                            "input_rank": rank,
                            "output_rank": rank,
                            "score": None,
                        }
                        for rank, result in enumerate(fallback_results, start=1)
                    ],
                    fallback=True,
                )
            return fallback_results

    async def hybrid_search(
        self,
        query: str,
        user_id: int,
        document_ids: list[int],
        top_k: int = 5,
        trace: EvaluationTrace | None = None,
    ) -> List[RetrievalResult]:
        logger.info(f"executing hybrid search for query='{query[:30]}...' user_id={user_id}")

        vector_results, bm25_results = await asyncio.gather(
            self.vector_search(
                query=query,
                document_ids=document_ids,
                top_k=top_k * CANDIDATE_MULTIPLIER,
                trace=trace,
            ),
            self.bm25_search(
                query=query,
                user_id=user_id,
                document_ids=document_ids,
                top_k=top_k * CANDIDATE_MULTIPLIER,
                trace=trace,
            ),
        )

        rrf_started = perf_counter()
        candidates = self.reciprocal_rank_fusion(
            vector_results=vector_results,
            bm25_results=bm25_results,
            top_k=top_k * CANDIDATE_MULTIPLIER,
            trace=trace,
        )
        if trace:
            trace.set_timing("rrf", (perf_counter() - rrf_started) * 1000)

        rerank_started = perf_counter()
        reranked = self.rerank(
            query=query,
            candidates=candidates,
            top_k=top_k,
            trace=trace,
        )
        if trace:
            trace.set_timing("reranking", (perf_counter() - rerank_started) * 1000)

        logger.info(f"hybrid search completed, returned {len(reranked)} chunks")
        return reranked
