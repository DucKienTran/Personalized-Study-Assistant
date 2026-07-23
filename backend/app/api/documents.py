from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from pydantic import BaseModel

from app.core.dependencies import (
    CurrentUserDep,
    DocumentProcessingServiceDep,
    DocumentServiceDep,
    SummaryRecordServiceDep,
    SummaryServiceDep,
    get_current_user,
)
from app.schemas.document_schema import DocumentContentOut, DocumentOut
from app.schemas.response_schema import BaseResponse
from app.schemas.summary_schema import (
    OverwriteSummaryRequest,
    SaveSummaryRequest,
    SummaryOut,
)

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
    dependencies=[Depends(get_current_user)],
)


class SummarizeRequest(BaseModel):
    document_id: int
    level: str = "normal"
    format: str = "markdown"
    instruction: Optional[str] = ""


@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
    response_model=BaseResponse[DocumentOut],
)
async def upload_and_process_document(
    background_tasks: BackgroundTasks,
    doc_service: DocumentServiceDep,
    processing_service: DocumentProcessingServiceDep,
    current_user: CurrentUserDep,
    file: UploadFile = File(...),
):
    file_bytes = await file.read()

    new_doc = await doc_service.upload_and_init_document(
        file_bytes=file_bytes, filename=file.filename, user_id=current_user.id
    )

    background_tasks.add_task(
        processing_service.execute_processing_pipeline,
        document_id=new_doc.id,
        mongo_id=new_doc.mongo_id,
        object_name=new_doc.file_path,
    )

    return BaseResponse(
        message="Tài liệu đã được tải lên thành công. Tiến trình phân tích cấu trúc đang được xử lý tự động.",
        data=new_doc,
    )


@router.post("/summarize", status_code=status.HTTP_200_OK, response_model=BaseResponse)
async def summarize_document(
    payload: SummarizeRequest,
    doc_service: DocumentServiceDep,
    summary_service: SummaryServiceDep,
    current_user: CurrentUserDep,
):
    doc_record = doc_service.get_document(
        user_id=current_user.id,
        document_id=payload.document_id,
    )
    if not doc_record or not doc_record.mongo_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")

    summary_result = await summary_service.generate_summary(
        mongo_id=doc_record.mongo_id,
        level=payload.level,
        format_type=payload.format,
        instruction=payload.instruction,
    )
    return BaseResponse(data={"summary_text": summary_result})


@router.post(
    "/summaries", status_code=status.HTTP_201_CREATED, response_model=BaseResponse
)
async def save_summary(
    payload: SaveSummaryRequest,
    summary_record_service: SummaryRecordServiceDep,
    current_user: CurrentUserDep,
):
    config = {
        "level": payload.level,
        "format": payload.format,
        "instruction": payload.instruction,
    }
    result = await summary_record_service.save_summary(
        user_id=current_user.id,
        document_id=payload.document_id,
        title=payload.title,
        summary_text=payload.summary_text,
        config=config,
    )
    return BaseResponse(data=result)


@router.put(
    "/summaries/{summary_id}",
    status_code=status.HTTP_200_OK,
    response_model=BaseResponse,
)
async def update_summary(
    summary_id: int,
    payload: OverwriteSummaryRequest,
    summary_record_service: SummaryRecordServiceDep,
    current_user: CurrentUserDep,
):
    result = await summary_record_service.update_summary(
        user_id=current_user.id,
        summary_id=summary_id,
        summary_text=payload.summary_text,
        title=payload.title,
    )
    return BaseResponse(data=result)


@router.get(
    "/summaries",
    status_code=status.HTTP_200_OK,
    response_model=BaseResponse[list[SummaryOut]],
)
async def get_summary_history(
    summary_record_service: SummaryRecordServiceDep,
    current_user: CurrentUserDep,
    document_id: Optional[int] = Query(None),
):
    history = summary_record_service.get_summary_history_list(
        user_id=current_user.id, document_id=document_id
    )
    return BaseResponse(data=history)


@router.get(
    "/summaries/{summary_id}",
    status_code=status.HTTP_200_OK,
    response_model=BaseResponse,
)
async def get_summary_detail(
    summary_id: int,
    summary_record_service: SummaryRecordServiceDep,
    current_user: CurrentUserDep,
):
    detail = await summary_record_service.get_summary_detail(
        user_id=current_user.id, summary_id=summary_id
    )
    return BaseResponse(data=detail)


@router.get(
    "/", status_code=status.HTTP_200_OK, response_model=BaseResponse[list[DocumentOut]]
)
async def get_documents(
    doc_service: DocumentServiceDep,
    current_user: CurrentUserDep,
    document_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, le=100),
):
    if document_id:
        doc = doc_service.get_document(
            user_id=current_user.id,
            document_id=document_id,
        )

        if doc is None:
            raise HTTPException(404, "Không tìm thấy tài liệu")

        return BaseResponse(data=[doc])

    docs = doc_service.list_documents(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        status_filter=status_filter,
    )

    return BaseResponse(data=docs)


@router.get(
    "/{document_id}/content",
    response_model=BaseResponse[DocumentContentOut],
)
async def get_document_raw_content(
    document_id: int,
    current_user: CurrentUserDep,
    document_service: DocumentServiceDep,
):
    content = await document_service.get_document_content(
        document_id=document_id,
        user_id=current_user.id,
    )

    if content is None:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy tài liệu",
        )

    return BaseResponse(data=DocumentContentOut.model_validate(content))


@router.delete(
    "/{document_id}", status_code=status.HTTP_200_OK, response_model=BaseResponse
)
async def delete_document(
    document_id: int,
    doc_service: DocumentServiceDep,
    current_user: CurrentUserDep,
):
    success = await doc_service.delete_document(document_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
    return BaseResponse(message="Đã xóa tài liệu")
