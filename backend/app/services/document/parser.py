import asyncio
from datetime import UTC, datetime
import logging

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

    def _extract_text_sync(self, file_bytes: bytes, filename: str) -> tuple[int, str]:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        total_pages = len(doc)

        if total_pages > PDF_PAGE_LIMIT:
            doc.close()
            raise BadRequestError(PDF_LIMIT_MESSAGE)

        extracted_text = ""
        for page_num in range(total_pages):
            page = doc.load_page(page_num)
            extracted_text += f"\n--- Trang {page_num + 1} ---\n"
            extracted_text += page.get_text()

        doc.close()
        return total_pages, extracted_text

    async def parse_document(self, file_bytes: bytes, filename: str):
        """
        Xử lý bóc tách văn bản từ PDF và lưu vào MongoDB.
        Đã được tối ưu bất đồng bộ, không gây nghẽn server.
        """
        try:
            logger.info(f"[Parser] Bắt đầu xử lý file: {filename}")

            total_pages, extracted_text = await asyncio.to_thread(
                self._extract_text_sync, file_bytes, filename
            )

            document_data = {
                "title": filename,
                "total_pages": total_pages,
                "content_raw": extracted_text,
                "status": "parsed",
                "created_at": datetime.now(UTC),
            }

            result = await self.collection.insert_one(document_data)
            logger.info(
                f"[Parser] Đã lưu thành công vào MongoDB. ID: {result.inserted_id}"
            )

            return {
                "document_id": str(result.inserted_id),
                "title": filename,
                "pages": total_pages,
                "status": "parsed",
            }

        except AppError:
            raise
        except Exception as e:
            logger.error(f"[Parser] Lỗi nghiêm trọng khi xử lý {filename}: {str(e)}")
            raise InternalServerError("Lỗi trích xuất dữ liệu tài liệu.")
