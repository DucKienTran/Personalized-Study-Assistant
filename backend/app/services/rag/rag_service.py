# app/services/ai/rag_service.py
import asyncio
from dataclasses import asdict
import logging
import re
from time import perf_counter
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.ai.llm.base import LLMClient
from app.ai.prompts.rag_prompt import RAGPromptBuilder
from app.models.document_model import Document as SQLDocument
from app.models.notebook_model import NotebookDocument
from app.schemas.rag_schema import RAGQueryResponse
from app.services.rag.evaluation_trace import EvaluationTrace, create_evaluation_trace
from app.services.rag.retrieval_models import (
    CitationSource,
    RAGResponse,
    RetrievalResult,
)
from app.services.rag.retrieval_service import (
    CANDIDATE_MULTIPLIER,
    RERANKER_MODEL,
    RRF_K,
    RetrievalService,
)

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
        notebook_id: int,
        top_k: int = 8,
        chat_history: Optional[List[Dict[str, str]]] = None,
        trace: EvaluationTrace | None = None,
    ) -> Tuple[
        List[RetrievalResult],
        List[CitationSource],
        str,
        dict,
    ]:
        rewrite_started = perf_counter()
        search_query = await self.rewrite_query(
            query,
            chat_history,
        )
        if trace:
            trace.set_timing("query_rewrite", (perf_counter() - rewrite_started) * 1000)

        active_document_rows = (
            sql_db.query(NotebookDocument.document_id)
            .filter(
                NotebookDocument.notebook_id == notebook_id,
                NotebookDocument.is_active.is_(True),
            )
            .all()
        )

        document_ids = [row.document_id for row in active_document_rows]
        if trace:
            trace.set_query_details(
                rewritten_query=search_query,
                notebook_id=notebook_id,
                active_document_ids=document_ids,
            )

        metadata = {
            "original_query": query,
            "rewritten_query": search_query,
            "retrieved_chunks": 0,
            "context_chunks": 0,
            "used_reranker": True,
        }

        if not document_ids:
            if trace:
                trace.set_timing("total_retrieval", 0.0)
                trace.set_timing("context_building", 0.0)
            return [], [], "", metadata

        docs = (
            sql_db.query(SQLDocument.id, SQLDocument.title)
            .filter(SQLDocument.id.in_(document_ids))
            .all()
        )
        doc_title_map = {doc.id: doc.title for doc in docs}

        retrieval_started = perf_counter()
        retrieved_chunks = await self.retrieval_service.hybrid_search(
            query=search_query,
            user_id=user_id,
            document_ids=document_ids,
            document_titles=doc_title_map,
            top_k=top_k,
            trace=trace,
        )
        if trace:
            trace.set_timing("total_retrieval", (perf_counter() - retrieval_started) * 1000)

        metadata["retrieved_chunks"] = len(retrieved_chunks)

        context_started = perf_counter()
        ordered_chunks = _reorder_chunks_lost_in_the_middle(retrieved_chunks)

        context_blocks = []
        citation_sources = []

        for position, chunk in enumerate(ordered_chunks, start=1):
            # Citation numbers follow final context order so reranked and
            # neighboring chunks always receive deterministic unique IDs.
            idx = position

            doc_title = doc_title_map.get(
                chunk.document_id,
                f"Tài liệu #{chunk.document_id}",
            )

            header_str = " > ".join(chunk.header_path) if chunk.header_path else "Không có mục"

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
        if trace:
            trace.set_context_order(
                [
                    {
                        "context_position": position,
                        "chunk_id": chunk.chunk_id,
                        "document_id": chunk.document_id,
                        "reranker_rank": chunk.rank,
                        "citation_index": position,
                        "context_role": chunk.context_role,
                        "neighbor_of": chunk.neighbor_of,
                    }
                    for position, chunk in enumerate(ordered_chunks, start=1)
                ]
            )
            trace.set_timing("context_building", (perf_counter() - context_started) * 1000)

        return (
            ordered_chunks,
            citation_sources,
            full_context,
            metadata,
        )

    # NOTE: unused elsewhere in the codebase per your own check — flagged for
    # removal. Left in place until you confirm no router still calls it
    # (removing here without checking callers could break an import).
    async def answer_question(
        self,
        query: str,
        user_id: int,
        sql_db: Session,
        notebook_id: int,
        top_k: int = 8,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> RAGResponse:
        trace = create_evaluation_trace(
            original_query=query,
            top_k=top_k,
            streaming=False,
            reranker_model=RERANKER_MODEL,
            candidate_multiplier=CANDIDATE_MULTIPLIER,
            rrf_k=RRF_K,
        )
        try:
            (
                chunks,
                citation_sources,
                full_context,
                metadata,
            ) = await self._prepare_context(
                query=query,
                user_id=user_id,
                sql_db=sql_db,
                notebook_id=notebook_id,
                top_k=top_k,
                chat_history=chat_history,
                trace=trace,
            )

            if not chunks:
                prompt = RAGPromptBuilder.build_no_context_prompt(query)

                llm_started = perf_counter()
                answer = await self.llm_client.generate(prompt)
                if trace:
                    trace.set_timing("llm_total", (perf_counter() - llm_started) * 1000)

                response = RAGQueryResponse(
                    answer=answer,
                    sources=[],
                    metadata=metadata,
                )
                if trace:
                    trace.finish(status="completed", answer_characters=len(answer))
                return response

            prompt = RAGPromptBuilder.build(query=query, context_text=full_context)

            logger.info(f"[RAGService] sending request to llm with {len(chunks)} chunks")
            llm_started = perf_counter()
            llm_answer = await self.llm_client.generate(prompt)
            if trace:
                trace.set_timing("llm_total", (perf_counter() - llm_started) * 1000)
            final_answer, final_sources, _ = _postprocess_citations(llm_answer, citation_sources)
            if trace:
                trace.set_citations(
                    [
                        {
                            "citation_index": source.index,
                            "chunk_id": source.chunk_id,
                            "document_id": source.document_id,
                        }
                        for source in final_sources
                    ]
                )

            response = RAGQueryResponse(
                answer=final_answer,
                sources=final_sources,
                metadata=metadata,
            )
            if trace:
                trace.finish(status="completed", answer_characters=len(final_answer))
            return response
        except Exception as exc:
            if trace:
                trace.finish(status="error", error=exc)
            raise

    async def stream_answer_question(
        self,
        query: str,
        user_id: int,
        sql_db: Session,
        notebook_id: int,
        top_k: int = 8,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ):
        """
        Cancellation: when the client aborts the HTTP request (Stop button ->
        AbortController.abort() on the frontend), Starlette cancels the task
        driving this generator, which raises asyncio.CancelledError at
        whatever `await`/`yield` point we're suspended on. We catch it here
        purely to log a clean, expected message instead of an unhandled
        traceback, then re-raise immediately — never swallow CancelledError,
        or the task won't actually stop and asyncio will warn about it.

        This does NOT by itself guarantee the in-flight call to Gemini stops
        generating server-side — that depends on whether
        `LLMClient.generate_stream` propagates cancellation down into its
        underlying HTTP stream (e.g. an `async with client.stream(...)`
        block that closes on cancellation). Worth checking there too if you
        want to avoid paying for tokens generated after the user hit Stop.
        """
        trace = create_evaluation_trace(
            original_query=query,
            top_k=top_k,
            streaming=True,
            reranker_model=RERANKER_MODEL,
            candidate_multiplier=CANDIDATE_MULTIPLIER,
            rrf_k=RRF_K,
        )
        stream_started = perf_counter()
        answer_characters = 0
        try:
            (
                chunks,
                citation_sources,
                full_context,
                metadata,
            ) = await self._prepare_context(
                query=query,
                user_id=user_id,
                sql_db=sql_db,
                notebook_id=notebook_id,
                top_k=top_k,
                chat_history=chat_history,
                trace=trace,
            )

            # Gửi metadata trước
            yield {
                "type": "metadata",
                "data": metadata,
            }

            if not chunks:
                prompt = RAGPromptBuilder.build_no_context_prompt(query)

                llm_started = perf_counter()
                first_token_seen = False
                async for token in self.llm_client.generate_stream(prompt):
                    if trace and not first_token_seen:
                        trace.set_timing("llm_ttft", (perf_counter() - llm_started) * 1000)
                        first_token_seen = True
                    answer_characters += len(token)
                    yield {
                        "type": "token",
                        "content": token,
                    }
                if trace:
                    trace.set_timing("llm_total", (perf_counter() - llm_started) * 1000)

                yield {
                    "type": "done",
                    "data": {},
                }
                if trace:
                    trace.set_timing("end_to_end_stream", (perf_counter() - stream_started) * 1000)
                    trace.finish(status="completed", answer_characters=answer_characters)
                return

            prompt = RAGPromptBuilder.build(
                query=query,
                context_text=full_context,
            )

            # Stream token
            full_answer_parts: List[str] = []
            llm_started = perf_counter()
            first_token_seen = False
            async for token in self.llm_client.generate_stream(prompt):
                if trace and not first_token_seen:
                    trace.set_timing("llm_ttft", (perf_counter() - llm_started) * 1000)
                    first_token_seen = True
                full_answer_parts.append(token)
                answer_characters += len(token)
                yield {"type": "token", "content": token}
            if trace:
                trace.set_timing("llm_total", (perf_counter() - llm_started) * 1000)

            full_answer = "".join(full_answer_parts)
            _, final_sources, citation_map = _postprocess_citations(full_answer, citation_sources)
            if trace:
                trace.set_citations(
                    [
                        {
                            "citation_index": source.index,
                            "chunk_id": source.chunk_id,
                            "document_id": source.document_id,
                        }
                        for source in final_sources
                    ]
                )

            yield {"type": "citation_map", "data": citation_map}
            yield {"type": "sources", "data": [asdict(s) for s in final_sources]}
            yield {"type": "done", "data": {}}
            if trace:
                trace.set_timing("end_to_end_stream", (perf_counter() - stream_started) * 1000)
                trace.finish(status="completed", answer_characters=len(full_answer))

        except asyncio.CancelledError:
            logger.info(
                "[RAGService] stream cancelled by client " "(notebook_id=%s, user_id=%s)",
                notebook_id,
                user_id,
            )
            if trace:
                trace.set_timing("end_to_end_stream", (perf_counter() - stream_started) * 1000)
                trace.finish(status="cancelled", answer_characters=answer_characters)
            raise
        except GeneratorExit:
            if trace:
                trace.set_timing("end_to_end_stream", (perf_counter() - stream_started) * 1000)
                trace.finish(status="cancelled", answer_characters=answer_characters)
            raise
        except Exception as exc:
            if trace:
                trace.set_timing("end_to_end_stream", (perf_counter() - stream_started) * 1000)
                trace.finish(
                    status="error",
                    answer_characters=answer_characters,
                    error=exc,
                )
            raise
