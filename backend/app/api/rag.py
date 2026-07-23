from fastapi import APIRouter, Depends, status

from fastapi.responses import StreamingResponse
import json

from app.core.config import settings
from app.core.dependencies import (
    CurrentUserDep,
    DbSession,
    DocumentServiceDep,
    RAGServiceDep,
    get_current_user,
)
from app.schemas.rag_schema import (
    RAGQueryRequest,
    RAGQueryResponse,
)
from app.schemas.response_schema import BaseResponse

router = APIRouter(
    prefix="/rag",
    tags=["RAG"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "/ask",
    response_model=BaseResponse[RAGQueryResponse],
    status_code=status.HTTP_200_OK,
)
async def ask_question(
    request: RAGQueryRequest,
    db: DbSession,
    current_user: CurrentUserDep,
    document_service: DocumentServiceDep,
    rag_service: RAGServiceDep,
):
    document_ids = document_service.list_document_ids(
        user_id=current_user.id,
    )

    if not document_ids:
        return BaseResponse(
            data=RAGQueryResponse(
                answer=(
                    "Bạn chưa có tài liệu nào sẵn sàng để trò chuyện. "
                    "Hãy tải lên tài liệu hoặc đợi quá trình xử lý hoàn tất."
                ),
                sources=[],
            )
        )

    response = await rag_service.answer_question(
        query=request.question,
        sql_db=db,
        document_ids=document_ids,
        top_k=settings.RAG_TOP_K,
    )

    return BaseResponse(data=response)


@router.post(
    "/stream",
    status_code=status.HTTP_200_OK,
)
async def stream_question(
    request: RAGQueryRequest,
    db: DbSession,
    current_user: CurrentUserDep,
    document_service: DocumentServiceDep,
    rag_service: RAGServiceDep,
):
    document_ids = document_service.list_document_ids(
        user_id=current_user.id,
    )

    if not document_ids:

        async def empty_stream():
            yield (
                "event: error\n"
                f"data: {json.dumps({'message': 'No documents available'}, ensure_ascii=False)}\n\n"
            )

        return StreamingResponse(
            empty_stream(),
            media_type="text/event-stream",
        )

    async def event_generator():
        try:
            async for event in rag_service.stream_answer_question(
                query=request.question,
                sql_db=db,
                document_ids=document_ids,
                top_k=settings.RAG_TOP_K,
            ):
                yield (
                    f"event: {event['type']}\n"
                    f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                )

        except Exception as exc:
            yield (
                "event: error\n"
                f"data: {json.dumps({'message': str(exc)}, ensure_ascii=False)}\n\n"
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
