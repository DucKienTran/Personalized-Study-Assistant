# app/api/endpoints/rag_router.py
import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.core.dependencies import (
    CurrentUserDep,
    DbSession,
    RAGServiceDep,
    get_current_user,
)
from app.schemas.rag_schema import RAGQueryRequest, RAGQueryResponse
from app.services.rag.conversation_service import ConversationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rag", tags=["Rag"], dependencies=[Depends(get_current_user)])

conversation_service = ConversationService()


@router.post("/query", response_model=RAGQueryResponse)
async def query_rag(
    payload: RAGQueryRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    rag_service: RAGServiceDep,
) -> RAGQueryResponse:
    return await rag_service.answer_question(
        query=payload.query,
        user_id=current_user.id,
        sql_db=db,
        notebook_id=payload.notebook_id,
        top_k=payload.top_k,
        chat_history=payload.chat_history,
    )


@router.post("/stream")
async def stream_query_rag(
    payload: RAGQueryRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    rag_service: RAGServiceDep,
):

    if payload.conversation_id:
        conv = conversation_service.get_conversation(db, current_user.id, payload.conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        conversation_id = conv.id
    else:
        conv = conversation_service.create_conversation(
            db,
            current_user.id,
            notebook_id=payload.notebook_id,
            title=payload.query[:60],
        )
        conversation_id = conv.id

    conversation_service.add_message(db, conversation_id, sender="user", content=payload.query)

    async def event_generator():
        full_answer_parts: list[str] = []
        final_sources: list = []
        yield f"event: conversation_id\ndata: {json.dumps({'id': conversation_id})}\n\n"

        try:
            async for chunk in rag_service.stream_answer_question(
                query=payload.query,
                user_id=current_user.id,
                sql_db=db,
                notebook_id=payload.notebook_id,
                top_k=payload.top_k,
                chat_history=payload.chat_history,
            ):
                if chunk["type"] == "token":
                    full_answer_parts.append(chunk["content"])
                if chunk["type"] == "sources":
                    final_sources = chunk["data"]

                event_type = chunk["type"]
                payload_data = chunk.get("data")
                if payload_data is None:
                    payload_data = chunk.get("content")

                yield (
                    f"event: {event_type}\n"
                    f"data: {json.dumps(payload_data, ensure_ascii=False)}\n\n"
                )

            conversation_service.add_message(
                db,
                conversation_id,
                sender="ai",
                content="".join(full_answer_parts),
                sources_json=json.dumps(final_sources, ensure_ascii=False),
            )

        except asyncio.CancelledError:
            # Client disconnected (Stop button -> AbortController.abort()).
            # Starlette already cancels this task on disconnect; we only
            # need to persist whatever partial answer we'd streamed so far
            # before re-raising. add_message() is a plain sync SQLAlchemy
            # call (no `await`), so it isn't itself subject to being
            # re-cancelled mid-write — cancellation only takes effect at
            # await points, and there are none in this block.
            logger.info(
                "RAG stream cancelled by client (conversation_id=%s)",
                conversation_id,
            )

            if full_answer_parts:
                conversation_service.add_message(
                    db,
                    conversation_id,
                    sender="ai",
                    content="".join(full_answer_parts),
                    sources_json=json.dumps(final_sources, ensure_ascii=False),
                )

            raise

    return StreamingResponse(event_generator(), media_type="text/event-stream")
