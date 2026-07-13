import asyncio
from datetime import UTC, datetime
import logging
from pathlib import Path
from io import BytesIO

from docx import Document
import fitz

from app.exceptions import AppError, BadRequestError, InternalServerError

logger = logging.getLogger(__name__)

PDF_PAGE_LIMIT = 15

PDF_LIMIT_MESSAGE = (
    "Tài khoản hiện tại chỉ cho phép xử lý tối đa 15 trang. "
    "Vui lòng nâng cấp PRO để xử lý file lớn hơn."
)


class DocumentParserService:
    def __init__(self, mongo_db):
        self.db = mongo_db
        self.collection = self.db["parsed_documents"]

    def _extract_pdf(self, file_bytes: bytes) -> tuple[int, str]:
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        try:
            total_pages = len(doc)

            if total_pages > PDF_PAGE_LIMIT:
                raise BadRequestError(PDF_LIMIT_MESSAGE)

            extracted_text = ""

            for page_num, page in enumerate(doc):
                extracted_text += f"\n--- Trang {page_num + 1} ---\n"
                extracted_text += page.get_text()

            return total_pages, extracted_text

        finally:
            doc.close()

    def _extract_docx(self, file_bytes: bytes) -> tuple[int, str]:
        doc = Document(BytesIO(file_bytes))

        paragraphs = []

        for paragraph in doc.paragraphs:
            text = paragraph.text.strip()
            if text:
                paragraphs.append(text)

        extracted_text = "\n\n".join(paragraphs)

        # DOCX không có khái niệm page cố định
        total_pages = 1

        return total_pages, extracted_text

    def _extract_pdf_scan(self, file_bytes: bytes) -> tuple[int, str]:
        """
        TODO:
        OCR cho PDF Scan.

        Có thể dùng:
        - Tesseract
        - PaddleOCR
        - Gemini OCR

        Hàm này sẽ được gọi nếu PDF không trích xuất được text.
        """
        raise BadRequestError("PDF Scan hiện chưa được hỗ trợ.")

    def _parse_document_sync(
        self,
        file_bytes: bytes,
        filename: str,
    ) -> tuple[int, str]:
        extension = Path(filename).suffix.lower()

        if extension == ".pdf":
            return self._extract_pdf(file_bytes)

        if extension == ".docx":
            return self._extract_docx(file_bytes)

        raise BadRequestError("Hệ thống hiện chỉ hỗ trợ PDF.")

    async def parse_document(
        self,
        file_bytes: bytes,
        filename: str,
    ):
        """
        Parse tài liệu và lưu MongoDB.
        """

        try:
            logger.info(f"[Parser] Bắt đầu xử lý file: {filename}")

            total_pages, extracted_text = await asyncio.to_thread(
                self._parse_document_sync,
                file_bytes,
                filename,
            )

            document_data = {
                "title": filename,
                "total_pages": total_pages,
                "content_raw": extracted_text,
                "status": "parsed",
                "created_at": datetime.now(UTC),
            }

            result = await self.collection.insert_one(document_data)

            logger.info(f"[Parser] Đã lưu MongoDB thành công. ID={result.inserted_id}")

            return {
                "document_id": str(result.inserted_id),
                "title": filename,
                "pages": total_pages,
                "status": "parsed",
            }

        except AppError:
            raise

        except Exception:
            logger.exception(f"[Parser] Lỗi khi xử lý file {filename}")
            raise InternalServerError("Lỗi trích xuất dữ liệu tài liệu.")
