# app/api/endpoints/rag_router.py
import asyncio
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.core.dependencies import (
    AssistantActionExecutorDep,
    AssistantActionRouterDep,
    ConversationTitleAIServiceDep,
    CurrentUserDep,
    DbSession,
    RAGServiceDep,
    get_current_user,
)
from app.schemas.rag_schema import RAGQueryRequest, RAGQueryResponse
from app.services.assistant.contracts import AssistantActionType
from app.services.rag.conversation_service import (
    DEFAULT_CONVERSATION_TITLE,
    ConversationService,
)

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
    background_tasks: BackgroundTasks,
    current_user: CurrentUserDep,
    db: DbSession,
    rag_service: RAGServiceDep,
    conversation_title_ai_service: ConversationTitleAIServiceDep,
    assistant_action_router: AssistantActionRouterDep,
    assistant_action_executor: AssistantActionExecutorDep,
):

    if payload.conversation_id:
        conv = conversation_service.get_conversation(db, current_user.id, payload.conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conv.notebook_id != payload.notebook_id:
            raise HTTPException(status_code=404, detail="Conversation not found")
        conversation_id = conv.id
        should_generate_title = (
            conv.title == DEFAULT_CONVERSATION_TITLE
            and not conversation_service.has_user_messages(db, conversation_id)
        )
    else:
        conv = conversation_service.create_conversation(
            db,
            current_user.id,
            notebook_id=payload.notebook_id,
            title=DEFAULT_CONVERSATION_TITLE,
        )
        conversation_id = conv.id
        should_generate_title = True

    conversation_service.add_message(db, conversation_id, sender="user", content=payload.query)

    async def event_generator():
        full_answer_parts: list[str] = []
        final_sources: list = []
        yield f"event: conversation_id\ndata: {json.dumps({'id': conversation_id})}\n\n"

        try:
            decision = await assistant_action_router.decide(user_message=payload.query)
            if decision.action != AssistantActionType.ANSWER:
                result = await assistant_action_executor.execute(
                    action=decision.action,
                    notebook_id=payload.notebook_id,
                    current_user=current_user,
                    user_message=payload.query,
                )
                message = result.message
                resource = result.resource
                if result.background_job is not None:
                    job = result.background_job
                    background_tasks.add_task(job.func, *job.args, **job.kwargs)
                full_answer_parts.append(message)
                resource_data = resource.to_event()["data"]
                yield (
                    "event: token\n"
                    f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
                )
                yield (
                    "event: resource\n"
                    f"data: {json.dumps(resource_data, ensure_ascii=False)}\n\n"
                )
                conversation_service.add_message(
                    db,
                    conversation_id,
                    sender="ai",
                    content=message,
                    resource_json=json.dumps(resource_data, ensure_ascii=False),
                )
                yield "event: done\ndata: {}\n\n"
            else:
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

            if should_generate_title:
                try:
                    generated_title = await conversation_title_ai_service.generate_title(
                        first_user_message=payload.query,
                    )
                    if generated_title:
                        updated_conversation = conversation_service.update_title_if_default(
                            db,
                            current_user.id,
                            conversation_id,
                            generated_title,
                        )
                        if updated_conversation:
                            conversation_data = {
                                "id": updated_conversation.id,
                                "title": updated_conversation.title,
                                "updated_at": updated_conversation.updated_at.isoformat(),
                            }
                            yield (
                                "event: conversation_updated\n"
                                f"data: {json.dumps(conversation_data, ensure_ascii=False)}\n\n"
                            )
                except Exception:
                    db.rollback()
                    logger.exception(
                        "Failed to generate or persist conversation title "
                        "(conversation_id=%s)",
                        conversation_id,
                    )

        except Exception as exc:
            db.rollback()
            logger.exception(
                "Assistant stream failed (conversation_id=%s)", conversation_id
            )
            detail = getattr(exc, "detail", None)
            message = detail if isinstance(detail, str) else str(exc)
            yield (
                "event: error\n"
                f"data: {json.dumps({'message': message or 'Assistant action failed.'}, ensure_ascii=False)}\n\n"
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
