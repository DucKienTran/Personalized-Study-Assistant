import logging

from fastapi import HTTPException, status
import fitz

logger = logging.getLogger(__name__)


class DocumentParserService:
    def parse_document(self, file_bytes: bytes, filename: str):
        logger.info(f"[parser] xử lý file: {filename}")
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        total_pages = len(doc)

        if total_pages > 15:
            doc.close()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="vượt giới hạn 15 trang."
            )

        extracted_text = ""
        for page_num in range(total_pages):
            page = doc.load_page(page_num)
            extracted_text += f"\n--- trang {page_num + 1} ---\n"
            extracted_text += page.get_text()

        doc.close()
        return total_pages, extracted_text
