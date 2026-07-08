import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel

from app.ai.summarizer import AISummarizerService
from app.api.dependencies import (
    get_ai_summarizer_service,
    get_current_user,
    get_document_crud_service,
    get_document_parser_service,
)
from app.services.document.crud import DocumentCRUDService
from app.services.document.parser import DocumentParserService

router = APIRouter(prefix="/documents", tags=["Documents"])


class SummarizeRequest(BaseModel):
    document_id: int  # Giữ nguyên int vì đây là ID của bảng MySQL
    level: str = "normal"  # short | normal | detailed
    format: str = "markdown"  # paragraph | bullet | markdown
    instruction: Optional[str] = ""


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_and_process_document(
    file: UploadFile = File(...),
    parser_service: DocumentParserService = Depends(get_document_parser_service),
    crud_service: DocumentCRUDService = Depends(get_document_crud_service),
    current_user=Depends(get_current_user),  # 👈 Cần thông tin user để lưu vào MySQL
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hệ thống chỉ hỗ trợ xử lý tài liệu định dạng PDF.",
        )

    # 1. Trích xuất text từ file PDF
    file_bytes = await file.read()
    total_pages, extracted_text = await asyncio.to_thread(
        parser_service._extract_text_sync, file_bytes, file.filename
    )

    # 2. Đồng bộ lưu vào CẢ MongoDB và MySQL thông qua crud_service
    new_doc = await crud_service.create_document(
        user_id=current_user.id,
        filename=file.filename,
        total_pages=total_pages,
        text=extracted_text,
    )

    # 3. Trả về thông tin bản ghi MySQL (Có document_id dạng số nguyên)
    return {
        "status": "success",
        "message": "Đã đọc và lưu trữ tài liệu thành công.",
        "data": {
            "document_id": new_doc.id,  # 👈 TRẢ VỀ ID SỐ NGUYÊN ĐỂ GET VÀ SUMMARIZE
            "title": new_doc.title,
            "pages": total_pages,
            "status": new_doc.status,
        },
    }


@router.post("/summarize", status_code=status.HTTP_200_OK)
async def summarize_document(
    payload: SummarizeRequest,
    crud_service: DocumentCRUDService = Depends(get_document_crud_service),
    ai_service: AISummarizerService = Depends(get_ai_summarizer_service),
    current_user=Depends(get_current_user),
):
    # Tìm kiếm tài liệu bằng ID số nguyên trong MySQL
    doc_record = crud_service.get_documents(current_user.id, document_id=payload.document_id)
    if not doc_record or not doc_record.mongo_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")

    try:
        # Lấy trúng chuỗi mongo_id lưu trong bản ghi MySQL để gọi sang Gemini
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
