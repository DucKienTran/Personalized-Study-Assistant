# app/services/ai/rag_service.py
from dataclasses import asdict
import logging
from typing import Dict, List, Optional, Tuple
import re


from sqlalchemy.orm import Session

from app.ai.llm.base import LLMClient
from app.ai.prompts.rag_prompt import RAGPromptBuilder
from app.models.document_model import Document as SQLDocument
from app.schemas.rag_schema import RAGQueryResponse
from app.services.ai.retrieval_models import (
    CitationSource,
    RAGResponse,
    RetrievalResult,
)
from app.services.ai.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)

_CITATION_PATTERN = re.compile(r"\[(\d+)\]")


def _postprocess_citations(
    answer: str,
    citation_sources: List[CitationSource],
) -> Tuple[str, List[CitationSource], Dict[str, int]]:
    # collapse immediately-repeated markers: [2][2] -> [2]
    collapsed = re.sub(r"(\[\d+\])(\1)+", r"\1", answer)

    source_by_index = {s.index: s for s in citation_sources}

    seen_order: List[int] = []
    for match in _CITATION_PATTERN.finditer(collapsed):
        num = int(match.group(1))
        if num not in seen_order:
            seen_order.append(num)

    # drop hallucinated citation numbers that don't map to a real chunk
    valid_order = [n for n in seen_order if n in source_by_index]
    old_to_new = {old: new for new, old in enumerate(valid_order, start=1)}

    def _replace(match: "re.Match[str]") -> str:
        new_num = old_to_new.get(int(match.group(1)))
        return f"[{new_num}]" if new_num is not None else ""

    remapped_answer = _CITATION_PATTERN.sub(_replace, collapsed)

    remapped_sources = [
        CitationSource(
            index=old_to_new[old_idx],
            document_id=source_by_index[old_idx].document_id,
            document_title=source_by_index[old_idx].document_title,
            page_start=source_by_index[old_idx].page_start,
            page_end=source_by_index[old_idx].page_end,
            header_path=source_by_index[old_idx].header_path,
            chunk_id=source_by_index[old_idx].chunk_id,
            snippet=source_by_index[old_idx].snippet,
        )
        for old_idx in valid_order
    ]

    str_keyed_map = {str(k): v for k, v in old_to_new.items()}
    return remapped_answer, remapped_sources, str_keyed_map


def _reorder_chunks_lost_in_the_middle(
    chunks: List[RetrievalResult],
) -> List[RetrievalResult]:
    if len(chunks) <= 2:
        return chunks

    reordered = [None] * len(chunks)
    left = 0
    right = len(chunks) - 1

    for i, chunk in enumerate(chunks):
        if i % 2 == 0:
            reordered[left] = chunk
            left += 1
        else:
            reordered[right] = chunk
            right -= 1

    return [c for c in reordered if c is not None]


class RAGService:
    def __init__(self, retrieval_service: RetrievalService, llm_client: LLMClient):
        self.retrieval_service = retrieval_service
        self.llm_client = llm_client

    async def rewrite_query(
        self, query: str, chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        if not chat_history:
            return query.strip()

        prompt = RAGPromptBuilder.build_rewrite_query_prompt(query, chat_history)

        try:
            rewritten = await self.llm_client.generate(prompt)
            cleaned = rewritten.strip()
            return cleaned if cleaned else query
        except Exception:
            logger.exception("failed to rewrite query, fallback to raw query")
            return query

    async def _prepare_context(
        self,
        query: str,
        user_id: int,
        sql_db: Session,
        document_ids: list[int],
        top_k: int = 5,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[
        List[RetrievalResult],
        List[CitationSource],
        str,
        dict,
    ]:
        search_query = await self.rewrite_query(
            query,
            chat_history,
        )

        retrieved_chunks = await self.retrieval_service.hybrid_search(
            query=search_query,
            user_id=user_id,
            document_ids=document_ids,
            top_k=top_k,
        )

        metadata = {
            "original_query": query,
            "rewritten_query": search_query,
            "retrieved_chunks": len(retrieved_chunks),
            "context_chunks": 0,
            "used_reranker": True,
        }

        if not retrieved_chunks:
            return [], [], "", metadata

        ordered_chunks = _reorder_chunks_lost_in_the_middle(retrieved_chunks)

        doc_ids = list({chunk.document_id for chunk in ordered_chunks})

        docs = (
            sql_db.query(SQLDocument.id, SQLDocument.title)
            .filter(SQLDocument.id.in_(doc_ids))
            .all()
        )

        doc_title_map = {doc.id: doc.title for doc in docs}

        context_blocks = []
        citation_sources = []

        for position, chunk in enumerate(ordered_chunks, start=1):
            # citation number = reranker rank (relevance-meaningful),
            # not physical position after lost-in-the-middle reordering
            idx = chunk.rank if chunk.rank is not None else position

            doc_title = doc_title_map.get(
                chunk.document_id,
                f"Tài liệu #{chunk.document_id}",
            )

            header_str = (
                " > ".join(chunk.header_path) if chunk.header_path else "Không có mục"
            )

            context_blocks.append(
                (
                    f"[{idx}] "
                    f"(Tài liệu: {doc_title} | "
                    f"Trang {chunk.page_start}-{chunk.page_end} | "
                    f"Mục: {header_str})\n"
                    f"{chunk.text}"
                )
            )

            citation_sources.append(
                CitationSource(
                    index=idx,
                    document_id=chunk.document_id,
                    document_title=doc_title,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    header_path=chunk.header_path,
                    chunk_id=chunk.chunk_id,
                    snippet=chunk.text[:300],
                )
            )

        full_context = "\n\n---\n\n".join(context_blocks)

        metadata["context_chunks"] = len(ordered_chunks)

        return (
            ordered_chunks,
            citation_sources,
            full_context,
            metadata,
        )

    async def answer_question(
        self,
        query: str,
        user_id: int,
        sql_db: Session,
        document_ids: list[int],
        top_k: int = 5,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> RAGResponse:
        (
            chunks,
            citation_sources,
            full_context,
            metadata,
        ) = await self._prepare_context(
            query=query,
            user_id=user_id,
            sql_db=sql_db,
            document_ids=document_ids,
            top_k=top_k,
            chat_history=chat_history,
        )

        if not chunks:
            prompt = RAGPromptBuilder.build_no_context_prompt(query)

            answer = await self.llm_client.generate(prompt)

            return RAGQueryResponse(
                answer=answer,
                sources=[],
                metadata=metadata,
            )

        prompt = RAGPromptBuilder.build(query=query, context_text=full_context)

        logger.info(f"[RAGService] sending request to llm with {len(chunks)} chunks")
        llm_answer = await self.llm_client.generate(prompt)
        final_answer, final_sources, _ = _postprocess_citations(
            llm_answer, citation_sources
        )

        return RAGQueryResponse(
            answer=final_answer,
            sources=final_sources,
            metadata=metadata,
        )

    async def stream_answer_question(
        self,
        query: str,
        user_id: int,
        sql_db: Session,
        document_ids: list[int],
        top_k: int = 5,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ):
        (
            chunks,
            citation_sources,
            full_context,
            metadata,
        ) = await self._prepare_context(
            query=query,
            user_id=user_id,
            sql_db=sql_db,
            document_ids=document_ids,
            top_k=top_k,
            chat_history=chat_history,
        )

        # Gửi metadata trước
        yield {
            "type": "metadata",
            "data": metadata,
        }

        if not chunks:
            prompt = RAGPromptBuilder.build_no_context_prompt(query)

            async for token in self.llm_client.generate_stream(prompt):
                yield {
                    "type": "token",
                    "content": token,
                }

            yield {
                "type": "done",
                "data": {},
            }
            return

        prompt = RAGPromptBuilder.build(
            query=query,
            context_text=full_context,
        )

        # Stream token
        full_answer_parts: List[str] = []
        async for token in self.llm_client.generate_stream(prompt):
            full_answer_parts.append(token)
            yield {"type": "token", "content": token}

        full_answer = "".join(full_answer_parts)
        _, final_sources, citation_map = _postprocess_citations(
            full_answer, citation_sources
        )

        yield {"type": "citation_map", "data": citation_map}
        yield {"type": "sources", "data": [asdict(s) for s in final_sources]}
        yield {"type": "done", "data": {}}
