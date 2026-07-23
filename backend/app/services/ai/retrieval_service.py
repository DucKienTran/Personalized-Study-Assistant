# app/services/ai/retrieval_service.py
import logging
import re
import asyncio
from typing import List
from chromadb.api import ClientAPI
from rank_bm25 import BM25Okapi

from app.core.config import settings
from app.services.ai.embedding_service import EmbeddingService
from app.services.ai.retrieval_models import RetrievalResult

logger = logging.getLogger(__name__)


def _tokenize_text(text: str) -> List[str]:
    """Tokenize đơn giản cho tiếng Việt / tiếng Anh bằng Regex."""
    return re.findall(r"\w+", text.lower())


class RetrievalService:
    def __init__(self, chroma_client: ClientAPI, embedding_service: EmbeddingService):
        self.chroma_client = chroma_client
        self.embedding_service = embedding_service
        self.chroma_collection = self.chroma_client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME
        )

    def vector_search(
        self, query: str, document_ids: list[int], top_k: int = 10
    ) -> List[RetrievalResult]:
        """Vector Search từ ChromaDB"""
        query_embedding = self.embedding_service.generate_query_embedding(query)

        results = self.chroma_collection.query(
            query_embeddings=[query_embedding],
            where={
                "document_id": {
                    "$in": document_ids,
                }
            },
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        retrieval_results = []
        if not results or not results["ids"] or not results["ids"][0]:
            return retrieval_results

        for chunk_id, text, meta, dist in zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # ChromaDB trả về distance, chuyển đổi thành cosine similarity score
            score = 1.0 - float(dist) if dist is not None else None

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
        return retrieval_results

    def _bm25_search_sync(
        self,
        query: str,
        document_ids: list[int],
        top_k: int = 10,
    ) -> List[RetrievalResult]:
        """
        BM25 Search trên tập tài liệu được chỉ định.
        """

        all_data = self.chroma_collection.get(
            where={
                "document_id": {
                    "$in": document_ids,
                }
            },
            include=[
                "documents",
                "metadatas",
            ],
        )

        if not all_data["documents"]:
            return []

        tokenized_corpus = [_tokenize_text(text) for text in all_data["documents"]]

        bm25 = BM25Okapi(tokenized_corpus)

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

            meta = all_data["metadatas"][idx]

            retrieval_results.append(
                RetrievalResult(
                    chunk_id=all_data["ids"][idx],
                    document_id=int(meta.get("document_id", 0)),
                    text=all_data["documents"][idx],
                    bm25_score=score,
                    page_start=int(meta.get("page_start") or 0),
                    page_end=int(meta.get("page_end") or 0),
                    header_path=meta.get("header_path", []),
                )
            )

        return retrieval_results

    # Hàm Wrapper của _bm25_search bọc asyncio.to_thread
    async def bm25_search(
        self, query: str, document_ids: list[int], top_k: int = 10
    ) -> List[RetrievalResult]:
        return await asyncio.to_thread(
            self._bm25_search_sync, query, document_ids, top_k
        )

    def reciprocal_rank_fusion(
        self,
        vector_results: List[RetrievalResult],
        bm25_results: List[RetrievalResult],
        k: int = 60,
        top_k: int = 5,
    ) -> List[RetrievalResult]:
        """Reciprocal Rank Fusion (RRF)."""

        rrf_scores: dict[str, float] = {}
        items_map: dict[str, RetrievalResult] = {}

        for rank, res in enumerate(vector_results, start=1):
            rrf_scores[res.chunk_id] = rrf_scores.get(res.chunk_id, 0.0) + (
                1.0 / (k + rank)
            )
            items_map[res.chunk_id] = res

        for rank, res in enumerate(bm25_results, start=1):
            rrf_scores[res.chunk_id] = rrf_scores.get(res.chunk_id, 0.0) + (
                1.0 / (k + rank)
            )

            if res.chunk_id in items_map:
                items_map[res.chunk_id].bm25_score = res.bm25_score
            else:
                items_map[res.chunk_id] = res

        sorted_chunk_ids = sorted(
            rrf_scores.keys(),
            key=lambda cid: rrf_scores[cid],
            reverse=True,
        )

        return [items_map[cid] for cid in sorted_chunk_ids[:top_k]]

    async def hybrid_search(
        self,
        query: str,
        document_ids: list[int],
        top_k: int = 5,
    ) -> List[RetrievalResult]:
        """
        Hybrid Search = Vector Search + BM25 + RRF.
        """

        vector_results = self.vector_search(
            query=query,
            document_ids=document_ids,
            top_k=top_k * 2,
        )

        bm25_results = await self.bm25_search(
            query=query,
            document_ids=document_ids,
            top_k=top_k * 2,
        )

        return self.reciprocal_rank_fusion(
            vector_results=vector_results,
            bm25_results=bm25_results,
            top_k=top_k,
        )
