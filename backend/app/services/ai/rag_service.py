# app/services/ai/rag_service.py
import logging

from sqlalchemy.orm import Session
from dataclasses import asdict
from app.ai.llm.base import LLMClient
from app.ai.prompts.rag_prompt import RAGPromptBuilder
from app.models.document_model import Document as SQLDocument
from app.services.ai.retrieval_models import (
    CitationSource,
    RAGResponse,
    RetrievalResult,
)
from app.services.ai.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self, retrieval_service: RetrievalService, llm_client: LLMClient):
        self.retrieval_service = retrieval_service
        self.llm_client = llm_client

    async def answer_question(
        self,
        query: str,
        sql_db: Session,
        document_ids: list[int],
        top_k: int = 5,
    ) -> RAGResponse:
        retrieved_chunks = await self.retrieval_service.hybrid_search(
            query=query, document_ids=document_ids, top_k=top_k
        )

        # Xử lý khi KHÔNG tìm thấy chunk nào
        if not retrieved_chunks:
            no_context_prompt = RAGPromptBuilder.build_no_context_prompt(query)
            fallback_answer = await self.llm_client.generate(no_context_prompt)
            return RAGResponse(
                answer=fallback_answer,
                sources=[],
            )

        # Query MySQL để lấy Map [document_id -> title]
        doc_ids = list({chunk.document_id for chunk in retrieved_chunks})
        docs = (
            sql_db.query(SQLDocument.id, SQLDocument.title)
            .filter(SQLDocument.id.in_(doc_ids))
            .all()
        )
        doc_title_map = {doc.id: doc.title for doc in docs}

        # Dựng Context & Danh sách Nguồn (Citation Sources)
        context_blocks = []
        citation_sources = []

        for idx, chunk in enumerate(retrieved_chunks, start=1):
            doc_title = doc_title_map.get(
                chunk.document_id, f"Tài liệu #{chunk.document_id}"
            )
            header_str = (
                " > ".join(chunk.header_path) if chunk.header_path else "Không có mục"
            )

            block = f"[{idx}] (Tài liệu: {doc_title} | Trang {chunk.page_start}-{chunk.page_end} | Mục: {header_str})\n{chunk.text}"
            context_blocks.append(block)

            citation_sources.append(
                CitationSource(
                    index=idx,
                    document_id=chunk.document_id,
                    document_title=doc_title,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    header_path=chunk.header_path,
                    chunk_id=chunk.chunk_id,
                )
            )

        full_context = "\n\n---\n\n".join(context_blocks)

        prompt = RAGPromptBuilder.build(query=query, context_text=full_context)

        logger.info(
            f"[RAGService] Sending request to LLM with {len(retrieved_chunks)} context chunks..."
        )
        llm_answer = await self.llm_client.generate(prompt)

        return RAGResponse(
            answer=llm_answer,
            sources=citation_sources,
        )

    async def stream_answer_question(
        self,
        query: str,
        sql_db: Session,
        document_ids: list[int],
        top_k: int = 5,
    ):
        retrieved_chunks = await self.retrieval_service.hybrid_search(
            query=query,
            document_ids=document_ids,
            top_k=top_k,
        )

        if not retrieved_chunks:
            prompt = RAGPromptBuilder.build_no_context_prompt(query)

            async for token in self.llm_client.generate_stream(prompt):
                yield {
                    "type": "token",
                    "content": token,
                }

            return

        doc_ids = list({chunk.document_id for chunk in retrieved_chunks})

        docs = (
            sql_db.query(SQLDocument.id, SQLDocument.title)
            .filter(SQLDocument.id.in_(doc_ids))
            .all()
        )

        doc_title_map = {doc.id: doc.title for doc in docs}

        context_blocks = []
        citation_sources = []

        for idx, chunk in enumerate(retrieved_chunks, start=1):
            doc_title = doc_title_map.get(
                chunk.document_id,
                f"Document #{chunk.document_id}",
            )

            block = (
                f"[{idx}] "
                f"(Document: {doc_title} | "
                f"Page {chunk.page_start}-{chunk.page_end})\n"
                f"{chunk.text}"
            )

            context_blocks.append(block)

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

        yield {
            "type": "sources",
            "data": [asdict(source) for source in citation_sources],
        }

        prompt = RAGPromptBuilder.build(
            query=query,
            context_text="\n\n---\n\n".join(context_blocks),
        )

        async for token in self.llm_client.generate_stream(prompt):
            yield {
                "type": "token",
                "content": token,
            }

        yield {
            "type": "done",
            "data": {},
        }
