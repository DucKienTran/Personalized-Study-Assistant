import logging

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.dependencies import get_current_user, get_document_parser_service
from app.schemas.document_schema import (
    DocumentUploadResponse,
    DocumentUploadResponseData,
    SummaryRequest,
    SummaryResponse,
    SummaryResponseData,
)
from app.schemas.user_schema import CurrentUser
from app.services.document.parser import DocumentParserService

router = APIRouter(prefix="/documents", tags=["Documents"])
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    parser_service: DocumentParserService = Depends(get_document_parser_service),
):
    """
    API tiếp nhận tải file: Xác thực token -> Lưu file vật lý -> Khởi tạo record 'pending' trong MySQL.
    """
    logger.info(f"User {current_user.id} đang thực hiện tải lên tài liệu: {file.filename}")

    new_doc = parser_service.create_document_record(file, current_user.id)

    return DocumentUploadResponse(
        message="Upload tài liệu thành công.",
        data=DocumentUploadResponseData(
            document_id=new_doc.id, title=new_doc.title, status=new_doc.status
        ),
    )


@router.post("/summary", response_model=SummaryResponse, status_code=status.HTTP_200_OK)
def summary_document(
    payload: SummaryRequest,
    current_user: CurrentUser = Depends(get_current_user),
    parser_service: DocumentParserService = Depends(get_document_parser_service),
):
    """
    API Tóm tắt tài liệu bằng AI (Chạy đồng bộ): Parse PDF qua PyMuPDF -> Gọi AI -> Lưu lịch sử vào MySQL -> Trả chi tiết.
    """
    logger.info(f"User {current_user.id} yêu cầu tóm tắt document_id: {payload.document_id}")

    updated_doc = parser_service.parse_and_summarize(payload.document_id, current_user.id)

    return SummaryResponse(
        message="Tóm tắt tài liệu thành công.",
        data=SummaryResponseData(
            document_id=updated_doc.id,
            title=updated_doc.title,
            status=updated_doc.status,
            parsed_content=updated_doc.parsed_content,
            summary_content=updated_doc.summary_content,
        ),
    )
