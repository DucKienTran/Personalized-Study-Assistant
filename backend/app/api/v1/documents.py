from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from pydantic import BaseModel

from app.ai.summarizer import AISummarizerService
from app.api.dependencies import (
    get_ai_summarizer_service,
    get_current_user,
    get_document_service,
    get_document_summary_service,
)
from app.schemas.document_schema import DocumentOut
from app.schemas.response_schema import BaseResponse
from app.schemas.summary_schema import OverwriteSummaryRequest, SaveSummaryRequest, SummaryOut
from app.services.document.document_service import DocumentService
from app.services.document.summary_service import DocumentSummaryService

router = APIRouter(prefix="/documents", tags=["Documents"])


class SummarizeRequest(BaseModel):
    document_id: int
    level: str = "normal"
    format: str = "markdown"
    instruction: Optional[str] = ""


@router.post("/upload", status_code=status.HTTP_201_CREATED, response_model=BaseResponse[DocumentOut])
async def upload_and_process_document(
    file: UploadFile = File(...),
    doc_service: DocumentService = Depends(get_document_service),
    current_user=Depends(get_current_user),
):
    file_bytes = await file.read()
    new_doc = await doc_service.upload_and_process_document(
        file_bytes=file_bytes, filename=file.filename, user_id=current_user.id
    )
    return BaseResponse(message="Đã đọc và lưu trữ tài liệu thành công.", data=new_doc)


@router.post("/summarize", status_code=status.HTTP_200_OK, response_model=BaseResponse)
async def summarize_document(
    payload: SummarizeRequest,
    doc_service: DocumentService = Depends(get_document_service),
    ai_service: AISummarizerService = Depends(get_ai_summarizer_service),
    current_user=Depends(get_current_user),
):
    doc_record = doc_service.get_documents(current_user.id, document_id=payload.document_id)
    if not doc_record or not doc_record.mongo_id:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")

    summary_result = await ai_service.generate_summary(
        mongo_id=doc_record.mongo_id,
        level=payload.level,
        format_type=payload.format,
        instruction=payload.instruction,
    )
    return BaseResponse(data={"summary": summary_result})


@router.post("/summaries", status_code=status.HTTP_201_CREATED, response_model=BaseResponse)
async def save_manual_summary(
    payload: SaveSummaryRequest,
    summary_service: DocumentSummaryService = Depends(get_document_summary_service),
    current_user=Depends(get_current_user),
):
    config = {"level": payload.level, "format": payload.format, "instruction": payload.instruction}
    result = await summary_service.save_manual_summary(
        user_id=current_user.id,
        document_id=payload.document_id,
        title=payload.title,
        summary_text=payload.summary_text,
        config=config,
    )
    return BaseResponse(data=result)


@router.put("/summaries/{summary_id}", status_code=status.HTTP_200_OK, response_model=BaseResponse)
async def overwrite_existing_summary(
    summary_id: int,
    payload: OverwriteSummaryRequest,
    summary_service: DocumentSummaryService = Depends(get_document_summary_service),
    current_user=Depends(get_current_user),
):
    result = await summary_service.overwrite_summary(
        user_id=current_user.id, summary_id=summary_id, summary_text=payload.summary_text
    )
    return BaseResponse(data=result)


@router.get(
    "/summaries", status_code=status.HTTP_200_OK, response_model=BaseResponse[list[SummaryOut]]
)
async def get_summary_history(
    document_id: Optional[int] = Query(None),
    summary_service: DocumentSummaryService = Depends(get_document_summary_service),
    current_user=Depends(get_current_user),
):
    history = summary_service.get_summary_history_list(
        user_id=current_user.id, document_id=document_id
    )
    return BaseResponse(data=history)


@router.get("/summaries/{summary_id}", status_code=status.HTTP_200_OK, response_model=BaseResponse)
async def get_summary_detail(
    summary_id: int,
    summary_service: DocumentSummaryService = Depends(get_document_summary_service),
    current_user=Depends(get_current_user),
):
    detail = await summary_service.get_summary_detail(
        user_id=current_user.id, summary_id=summary_id
    )
    return BaseResponse(data=detail)


@router.get("/", status_code=status.HTTP_200_OK, response_model=BaseResponse[list[DocumentOut]])
async def get_documents(
    document_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, le=100),
    doc_service: DocumentService = Depends(get_document_service),
    current_user=Depends(get_current_user),
):
    docs = doc_service.get_documents(current_user.id, skip, limit, status_filter, document_id)
    if document_id and not docs:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")

    if document_id:
        return BaseResponse(data=[docs])  
    return BaseResponse(data=docs)


@router.delete("/{document_id}", status_code=status.HTTP_200_OK, response_model=BaseResponse)
async def delete_document(
    document_id: int,
    doc_service: DocumentService = Depends(get_document_service),
    current_user=Depends(get_current_user),
):
    from fastapi import HTTPException

    success = await doc_service.delete_document(document_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
    return BaseResponse(message="Đã xóa tài liệu")
