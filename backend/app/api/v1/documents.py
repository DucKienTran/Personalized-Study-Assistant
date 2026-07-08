from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, Query
from pydantic import BaseModel

from app.api.dependencies import (
    get_document_parser_service,
    get_document_crud_service,
    get_ai_summarizer_service,
    get_current_user,
)
from app.services.document.parser import DocumentParserService
from app.services.document.crud import DocumentCRUDService
from app.ai.summarizer import AISummarizerService

router = APIRouter(prefix="/documents", tags=["Documents"])


from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel


class SummarizeRequest(BaseModel):
    document_id: int
    level: str = "normal"  # short | normal | detailed
    format: str = "markdown"  # paragraph | bullet | markdown
    instruction: Optional[str] = ""


@router.post("/summarize", status_code=status.HTTP_200_OK)
async def summarize_document(
    payload: SummarizeRequest,
    crud_service: DocumentCRUDService = Depends(get_document_crud_service),
    ai_service: AISummarizerService = Depends(get_ai_summarizer_service),
    current_user=Depends(get_current_user),
):
    doc_record = crud_service.get_documents(current_user.id, document_id=payload.document_id)
    if not doc_record or not doc_record.mongo_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")

    try:
        summary_result = await ai_service.generate_summary(
            mongo_id=doc_record.mongo_id,
            level=payload.level,
            format_type=payload.format,
            instruction=payload.instruction,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    crud_service.update_document_status(doc_record.id, "completed")

    return {
        "status": "success",
        "data": {
            "summary": summary_result,
            "config_used": {
                "level": payload.level,
                "format": payload.format,
                "instruction": payload.instruction,
            },
        },
    }


@router.get("/", status_code=status.HTTP_200_OK)
async def get_documents(
    document_id: Optional[int] = Query(None, description="Lấy chi tiết 1 document"),
    status_filter: Optional[str] = Query(None, description="Lọc theo trạng thái"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, le=100),
    crud_service: DocumentCRUDService = Depends(get_document_crud_service),
    current_user=Depends(get_current_user),
):
    docs = crud_service.get_documents(current_user.id, skip, limit, status_filter, document_id)

    if document_id and not docs:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")

    return {"status": "success", "data": docs}


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
async def delete_document(
    document_id: int,
    crud_service: DocumentCRUDService = Depends(get_document_crud_service),
    current_user=Depends(get_current_user),
):
    success = await crud_service.delete_document(document_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")

    return {"status": "success", "message": "Đã xóa tài liệu"}


@router.post("/summarize", status_code=status.HTTP_200_OK)
async def summarize_document(
    payload: SummarizeRequest,
    crud_service: DocumentCRUDService = Depends(get_document_crud_service),
    ai_service: AISummarizerService = Depends(get_ai_summarizer_service),
    current_user=Depends(get_current_user),
):
    doc_record = crud_service.get_documents(current_user.id, document_id=payload.document_id)
    if not doc_record or not doc_record.mongo_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")

    result = await ai_service.generate_summary(doc_record.mongo_id)
    crud_service.update_document_status(doc_record.id, "completed")

    return {"status": "success", "data": result}
