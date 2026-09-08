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
MAX_CONTEXT_CHUNKS = 12
MAX_CONTEXT_ESTIMATED_TOKENS = 10_000
CONTEXT_REDUNDANCY_THRESHOLD = 0.85
MAX_RETRIEVAL_QUERIES = 4
MAX_RERANK_CANDIDATES = 40
RRF_K = 60
RERANKER_MODEL = FLASHRANK_DEFAULT_MODEL


def _get_global_ranker() -> Ranker:
    global _global_ranker
    if _global_ranker is None:
        _global_ranker = Ranker(model_name=RERANKER_MODEL)
    return _global_ranker


def _tokenize_text(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())


def _normalize_for_overlap(text: str) -> str:
    return " ".join(_tokenize_text(text))


def _estimated_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _is_redundant(
    candidate: RetrievalResult,
    selected: List[RetrievalResult],
) -> bool:
    candidate_normalized = _normalize_for_overlap(candidate.text)
    candidate_tokens = set(candidate_normalized.split())
    for existing in selected:
        if candidate.chunk_id == existing.chunk_id:
            return True
        existing_normalized = _normalize_for_overlap(existing.text)
        if candidate_normalized and candidate_normalized == existing_normalized:
            return True
        existing_tokens = set(existing_normalized.split())
        union = candidate_tokens | existing_tokens
        if union and len(candidate_tokens & existing_tokens) / len(union) >= (
            CONTEXT_REDUNDANCY_THRESHOLD
        ):
            return True
    return False


def build_retrieval_queries(query: str) -> list[str]:
    original = " ".join(query.split())
    if not original:
        return [query]

    scope = ""
    requirements: list[str] = []
    bullet_matches = list(
        re.finditer(r"(?:^|\n)\s*(?:[-*\u2022]|\d+[.)])\s+([^\n]+)", query)
    )
    if len(bullet_matches) >= 2:
        scope = " ".join(query[: bullet_matches[0].start()].strip(" :\n").split())
        requirements = [match.group(1) for match in bullet_matches]
    else:
        numeric_requirements = list(
            re.finditer(
                r"\b\d+(?:[.,]\d+)?\s*(?:members?|users?|seats?|workspaces?|"
                r"mb|gb|tb|hours?|hrs?|days?|minutes?|mins?)\b",
                original,
                flags=re.IGNORECASE,
            )
        )
        has_numeric_list = len(numeric_requirements) >= 2 or (
            len(numeric_requirements) == 1
            and re.search(r"[,;]", original[numeric_requirements[0].end() :]) is not None
        )
        list_start = numeric_requirements[0].start() if has_numeric_list else None
        if list_start is None:
            comparison_match = re.search(r"\b(?:for|across|on)\s+", original, re.IGNORECASE)
            if comparison_match and re.search(r"[,;]", original[comparison_match.end() :]):
                list_start = comparison_match.end()
        if list_start is None and ":" in original:
            colon_index = original.index(":")
            if ";" in original[colon_index + 1 :]:
                list_start = colon_index + 1

        if list_start is not None:
            scope = original[:list_start].strip(" :,-")
            tail = original[list_start:].strip(" ?.!")
            requirements = re.split(
                r"\s*(?:,|;|\n)\s*|\s+(?:and|và)\s+",
                tail,
                flags=re.IGNORECASE,
            )

    requirements = [" ".join(item.strip(" ?.!").split()) for item in requirements]
    requirements = [item for item in requirements if item]
    if len(requirements) < 2:
        return [original]

    max_subqueries = MAX_RETRIEVAL_QUERIES - 1
    if len(requirements) > max_subqueries:
        requirements = [
            *requirements[: max_subqueries - 1],
            " and ".join(requirements[max_subqueries - 1 :]),
        ]

    subqueries = [f"{scope} {item}".strip() for item in requirements]
    return list(dict.fromkeys([original, *subqueries]))[:MAX_RETRIEVAL_QUERIES]


class RetrievalService:
    def __init__(
        self,
        chroma_client: ClientAPI,
        embedding_service: EmbeddingService,
        redis: Redis,
        collection_name: str | None = None,
    ):
        self.chroma_client = chroma_client
        self.embedding_service = embedding_service
        self.redis = redis
        self.chroma_collection = self.chroma_client.get_or_create_collection(
            name=collection_name or settings.CHROMA_COLLECTION_NAME
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
                    previous_chunk=meta.get("previous_chunk"),
                    next_chunk=meta.get("next_chunk"),
                    beir_corpus_id=meta.get("beir_corpus_id"),
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
                    "previous_chunk": meta.get("previous_chunk"),
                    "next_chunk": meta.get("next_chunk"),
                    "beir_corpus_id": meta.get("beir_corpus_id"),
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
                    previous_chunk=item.get("previous_chunk"),
                    next_chunk=item.get("next_chunk"),
                    beir_corpus_id=item.get("beir_corpus_id"),
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
                    "document_title": result.document_title,
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
            passages = []
            for res in candidates:
                parts = []
                if res.document_title:
                    parts.append(f"Document: {res.document_title}")
                if res.header_path:
                    parts.append(f"Section: {' > '.join(res.header_path)}")
                parts.append(res.text)
                passages.append(
                    {
                        "id": res.chunk_id,
                        "text": "\n\n".join(parts),
                    }
                )

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

    def _fetch_chunks_by_ids_sync(self, chunk_ids: list[str]) -> List[RetrievalResult]:
        unique_ids = list(dict.fromkeys(chunk_id for chunk_id in chunk_ids if chunk_id))
        if not unique_ids:
            return []

        results = self.chroma_collection.get(
            ids=unique_ids,
            include=["documents", "metadatas"],
        )
        if not results or not results.get("ids"):
            return []

        fetched = []
        for chunk_id, text, meta in zip(
            results["ids"],
            results.get("documents") or [],
            results.get("metadatas") or [],
        ):
            if text is None or meta is None:
                continue
            fetched.append(
                RetrievalResult(
                    chunk_id=chunk_id,
                    document_id=int(meta.get("document_id", 0)),
                    text=text,
                    page_start=int(meta.get("page_start") or 0),
                    page_end=int(meta.get("page_end") or 0),
                    header_path=meta.get("header_path", []),
                    previous_chunk=meta.get("previous_chunk"),
                    next_chunk=meta.get("next_chunk"),
                    context_role="neighbor",
                    beir_corpus_id=meta.get("beir_corpus_id"),
                )
            )
        return fetched

    async def fetch_chunks_by_ids(self, chunk_ids: list[str]) -> List[RetrievalResult]:
        return await asyncio.to_thread(self._fetch_chunks_by_ids_sync, chunk_ids)

    async def _expand_with_neighbors(
        self,
        reranked: List[RetrievalResult],
        trace: EvaluationTrace | None = None,
    ) -> List[RetrievalResult]:
        remaining_slots = MAX_CONTEXT_CHUNKS - len(reranked)
        estimated_context_tokens = sum(_estimated_tokens(result.text) for result in reranked)
        selected_ids = {result.chunk_id for result in reranked}
        requested_neighbors: list[str] = []
        neighbor_sources: dict[str, RetrievalResult] = {}
        redundant_neighbors_skipped = 0
        for result in reranked:
            for neighbor_id in (result.previous_chunk, result.next_chunk):
                if not neighbor_id:
                    continue
                if neighbor_id in selected_ids or neighbor_id in neighbor_sources:
                    redundant_neighbors_skipped += 1
                else:
                    requested_neighbors.append(neighbor_id)
                    neighbor_sources[neighbor_id] = result

        if remaining_slots <= 0 or not requested_neighbors:
            if trace:
                trace.set_context_packing(
                    {
                        "primary_count": len(reranked),
                        "neighbor_candidates": len(requested_neighbors),
                        "neighbors_added": 0,
                        "redundant_neighbors_skipped": redundant_neighbors_skipped,
                        "budget_skipped": 0,
                        "estimated_context_tokens": estimated_context_tokens,
                    }
                )
            return reranked

        fetched_by_id = {
            result.chunk_id: result
            for result in await self.fetch_chunks_by_ids(requested_neighbors)
        }
        neighbors = []
        budget_skipped = 0
        selected = list(reranked)
        section_counts: dict[tuple[str, ...], int] = {}
        for result in selected:
            section = tuple(result.header_path)
            section_counts[section] = section_counts.get(section, 0) + 1

        request_order = {chunk_id: index for index, chunk_id in enumerate(requested_neighbors)}
        for source in reranked:
            source_neighbors = [
                fetched_by_id[neighbor_id]
                for neighbor_id in requested_neighbors
                if neighbor_sources[neighbor_id].chunk_id == source.chunk_id
                and neighbor_id in fetched_by_id
                and fetched_by_id[neighbor_id].document_id == source.document_id
            ]
            source_neighbors.sort(
                key=lambda neighbor: (
                    section_counts.get(tuple(neighbor.header_path), 0),
                    request_order[neighbor.chunk_id],
                )
            )
            for neighbor in source_neighbors:
                if _is_redundant(neighbor, selected):
                    redundant_neighbors_skipped += 1
                    continue
                neighbor_tokens = _estimated_tokens(neighbor.text)
                if estimated_context_tokens + neighbor_tokens > MAX_CONTEXT_ESTIMATED_TOKENS:
                    budget_skipped += 1
                    continue
                neighbor.neighbor_of = source.chunk_id
                neighbors.append(neighbor)
                selected.append(neighbor)
                estimated_context_tokens += neighbor_tokens
                section = tuple(neighbor.header_path)
                section_counts[section] = section_counts.get(section, 0) + 1
                if len(neighbors) >= remaining_slots:
                    break
            if len(neighbors) >= remaining_slots:
                break

        if trace:
            trace.set_context_packing(
                {
                    "primary_count": len(reranked),
                    "neighbor_candidates": len(requested_neighbors),
                    "neighbors_added": len(neighbors),
                    "redundant_neighbors_skipped": redundant_neighbors_skipped,
                    "budget_skipped": budget_skipped,
                    "estimated_context_tokens": estimated_context_tokens,
                }
            )

        return [*reranked, *neighbors]

    async def hybrid_candidates(
        self,
        query: str,
        user_id: int,
        document_ids: list[int],
        top_k: int = 5,
        trace: EvaluationTrace | None = None,
    ) -> List[RetrievalResult]:
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
        return candidates

    @staticmethod
    def _merge_query_candidates(
        candidate_groups: list[List[RetrievalResult]],
    ) -> List[RetrievalResult]:
        if len(candidate_groups) == 1:
            return candidate_groups[0][:MAX_RERANK_CANDIDATES]

        merged: dict[str, dict[str, Any]] = {}
        seen_order = 0
        for query_index, candidates in enumerate(candidate_groups):
            for rank, candidate in enumerate(candidates, start=1):
                entry = merged.get(candidate.chunk_id)
                if entry is None:
                    entry = {
                        "result": candidate,
                        "query_hits": 0,
                        "best_rank": rank,
                        "original_rank": rank if query_index == 0 else None,
                        "seen_order": seen_order,
                    }
                    merged[candidate.chunk_id] = entry
                    seen_order += 1
                else:
                    result = entry["result"]
                    for score_field in ("vector_score", "bm25_score", "retrieval_score"):
                        current_score = getattr(result, score_field)
                        candidate_score = getattr(candidate, score_field)
                        if candidate_score is not None and (
                            current_score is None or candidate_score > current_score
                        ):
                            setattr(result, score_field, candidate_score)
                    entry["best_rank"] = min(entry["best_rank"], rank)
                    if query_index == 0:
                        entry["original_rank"] = rank
                entry["query_hits"] += 1

        ranked_entries = sorted(
            merged.values(),
            key=lambda entry: (
                -entry["query_hits"],
                entry["best_rank"],
                entry["original_rank"] if entry["original_rank"] is not None else float("inf"),
                entry["seen_order"],
            ),
        )
        return [entry["result"] for entry in ranked_entries[:MAX_RERANK_CANDIDATES]]

    async def hybrid_search(
        self,
        query: str,
        user_id: int,
        document_ids: list[int],
        document_titles: dict[int, str] | None = None,
        top_k: int = 5,
        trace: EvaluationTrace | None = None,
    ) -> List[RetrievalResult]:
        logger.info(f"executing hybrid search for query='{query[:30]}...' user_id={user_id}")
        retrieval_queries = build_retrieval_queries(query)
        if trace:
            trace.set_retrieval_queries(retrieval_queries)

        candidate_groups = await asyncio.gather(
            *[
                self.hybrid_candidates(
                    query=retrieval_query,
                    user_id=user_id,
                    document_ids=document_ids,
                    top_k=top_k,
                    trace=trace if index == 0 else None,
                )
                for index, retrieval_query in enumerate(retrieval_queries)
            ]
        )
        candidates = self._merge_query_candidates(candidate_groups)
        if document_titles:
            for candidate in candidates:
                candidate.document_title = document_titles.get(candidate.document_id)

        rerank_started = perf_counter()
        reranked = self.rerank(
            query=query,
            candidates=candidates,
            top_k=top_k,
            trace=trace,
        )
        if trace:
            trace.set_timing("reranking", (perf_counter() - rerank_started) * 1000)

        expanded = await self._expand_with_neighbors(reranked, trace=trace)
        if document_titles:
            for result in expanded:
                result.document_title = document_titles.get(result.document_id)
        logger.info(f"hybrid search completed, returned {len(expanded)} chunks")
        return expanded
