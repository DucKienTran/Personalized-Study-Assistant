import fitz  
import logging
import asyncio 
from fastapi import HTTPException, status
from datetime import datetime, timezone 

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentParserService:
    def __init__(self, mongo_db):
        self.db = mongo_db
        self.collection = self.db["parsed_documents"]

    def _extract_text_sync(self, file_bytes: bytes, filename: str) -> tuple[int, str]:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        total_pages = len(doc)
        
        # Kiểm tra giới hạn trang
        if total_pages > 15:
            doc.close()
            raise ValueError("limit_exceeded")
            
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
                "created_at": datetime.now(timezone.utc) 
            }
            
            result = await self.collection.insert_one(document_data)
            logger.info(f"[Parser] Đã lưu thành công vào MongoDB. ID: {result.inserted_id}")
            
            return {
                "document_id": str(result.inserted_id),
                "title": filename,
                "pages": total_pages,
                "status": "parsed"
            }
            
        except ValueError as ve:
            if str(ve) == "limit_exceeded":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tài khoản hiện tại chỉ cho phép xử lý tối đa 15 trang. Vui lòng nâng cấp PRO để xử lý file lớn hơn."
                )
            raise
        except HTTPException:
            raise 
        except Exception as e:
            logger.error(f"[Parser] Lỗi nghiêm trọng khi xử lý {filename}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Lỗi trích xuất dữ liệu tài liệu."
            )