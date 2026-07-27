# app/api/v1/endpoints/rag_router.py
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.core.dependencies import (
    CurrentUserDep,
    DbSession,
    DocumentServiceDep,
    RAGServiceDep,
    get_current_user,
)
from app.schemas.rag_schema import RAGQueryRequest, RAGQueryResponse
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/rag", tags=["Rag"], dependencies=[Depends(get_current_user)])

conversation_service = ConversationService()


def _resolve_document_ids(
    payload_doc_ids: list[int] | None,
    user_doc_ids: list[int],
) -> list[int]:
    if not payload_doc_ids:
        return user_doc_ids
    valid_set = set(user_doc_ids)
    return [doc_id for doc_id in payload_doc_ids if doc_id in valid_set]


@router.post("/query", response_model=RAGQueryResponse)
async def query_rag(
    payload: RAGQueryRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    rag_service: RAGServiceDep,
    document_service: DocumentServiceDep,
) -> RAGQueryResponse:
    user_doc_ids = document_service.list_document_ids(user_id=current_user.id)
    target_doc_ids = _resolve_document_ids(payload.document_ids, user_doc_ids)

    return await rag_service.answer_question(
        query=payload.query,
        user_id=current_user.id,
        sql_db=db,
        document_ids=target_doc_ids,
        top_k=payload.top_k,
        chat_history=payload.chat_history,
    )


@router.post("/stream")
async def stream_query_rag(
    payload: RAGQueryRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    rag_service: RAGServiceDep,
    document_service: DocumentServiceDep,
):
    user_doc_ids = document_service.list_document_ids(user_id=current_user.id)
    target_doc_ids = _resolve_document_ids(payload.document_ids, user_doc_ids)

    if payload.conversation_id:
        conv = conversation_service.get_conversation(db, current_user.id, payload.conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        conversation_id = conv.id
    else:
        conv = conversation_service.create_conversation(
            db, current_user.id, title=payload.query[:60]
        )
        conversation_id = conv.id

    conversation_service.add_message(db, conversation_id, sender="user", content=payload.query)
    async def event_generator():
        full_answer_parts: list[str] = []
        final_sources: list = []
        yield f"event: conversation_id\ndata: {json.dumps({'id': conversation_id})}\n\n"

        async for chunk in rag_service.stream_answer_question(
            query=payload.query,
            user_id=current_user.id,
            sql_db=db,
            document_ids=target_doc_ids,
            top_k=payload.top_k,
            chat_history=payload.chat_history,
        ):
            if chunk["type"] == "token":
                full_answer_parts.append(chunk["content"])
            if chunk["type"] == "sources":
                final_sources = chunk["data"]
            if chunk["type"] == "conversation_id":
                pass  # unreachable, placeholder for clarity

            event_type = chunk["type"]
            payload_data = chunk.get("data")
            if payload_data is None:
                payload_data = chunk.get("content")

            yield (
                f"event: {event_type}\n" f"data: {json.dumps(payload_data, ensure_ascii=False)}\n\n"
            )

        conversation_service.add_message(
            db,
            conversation_id,
            sender="ai",
            content="".join(full_answer_parts),
            sources_json=json.dumps(final_sources, ensure_ascii=False),
        )

    return StreamingResponse(event_generator(), media_type="text/event-stream")
