import logging
import os

from fastapi import HTTPException, UploadFile, status
import fitz
from sqlalchemy.orm import Session

from app.models.document_model import Document
from app.services.ai.summarizer import AISummarizerService
from app.utils.file_handler import validate_and_save_file

# KHỞI TẠO LOGGER CHO MODULE PARSER
logger = logging.getLogger(__name__)


class DocumentParserService:
    def __init__(self, db: Session):
        self.db = db

    def create_document_record(self, file: UploadFile, user_id: int) -> Document:
        """
        Nghiệp vụ lưu file vật lý và khởi tạo bản ghi 'pending' trong MySQL.
        """
        logger.info(
            f"[UPLOAD] Bắt đầu xử lý tải file cho user_id={user_id}. Tên file gốc: {file.filename}"
        )
        try:
            # Gọi hàm xử lý file từ file_handler
            file_path = validate_and_save_file(file)
            logger.info(f"[UPLOAD] Đã lưu file vật lý thành công tại đường dẫn: {file_path}")

            # Trích xuất định dạng file từ đuôi mở rộng
            _, ext = os.path.splitext(file.filename)
            file_type = ext.lower().replace(".", "")

            new_doc = Document(
                user_id=user_id,
                title=file.filename,
                file_path=file_path,
                file_type=file_type,
                status="pending",
            )

            self.db.add(new_doc)
            self.db.commit()
            self.db.refresh(new_doc)

            logger.info(
                f"[UPLOAD] Khởi tạo thành công bản ghi Document ID={new_doc.id} vào MySQL với trạng thái 'pending'."
            )
            return new_doc

        except HTTPException as http_e:
            # Các lỗi validate từ file_handler (sai định dạng file...)
            logger.warning(f"[UPLOAD] Thất bại do lỗi validate từ client: {http_e.detail}")
            raise http_e
        except Exception as e:
            self.db.rollback()
            logger.error(
                f"[UPLOAD] LỖI HỆ THỐNG NGHIÊM TRỌNG tại tầng Service: {str(e)}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi hệ thống tầng Service khi upload: {str(e)}",
            )

    def parse_and_summarize(self, document_id: int, user_id: int) -> Document:
        """
        Nghiệp vụ parse PDF bằng PyMuPDF (giới hạn 15 trang) và gọi AI tóm tắt đồng bộ.
        """
        logger.info(
            f"[SUMMARY] User_id={user_id} yêu cầu tóm tắt tài liệu Document ID={document_id}"
        )

        # 1. Kiểm tra tài liệu và quyền sở hữu
        doc_record = (
            self.db.query(Document)
            .filter(Document.id == document_id, Document.user_id == user_id)
            .first()
        )

        if not doc_record:
            logger.warning(
                f"[SUMMARY] Từ chối xử lý: Không tìm thấy Document ID={document_id} hoặc không thuộc sở hữu của user_id={user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy tài liệu hoặc bạn không có quyền truy cập.",
            )

        # 2. Phương án A: Nếu đã tóm tắt thành công trước đó thì trả về luôn kết quả cũ
        if doc_record.status == "completed" and doc_record.summary_content:
            logger.info(
                f"[SUMMARY] Bỏ qua gọi AI (Idempotency áp dụng): Document ID={document_id} đã có sẵn bản tóm tắt cũ. Trả kết quả ngay lập tức."
            )
            return doc_record

        # Cập nhật trạng thái đang xử lý
        doc_record.status = "processing"
        self.db.commit()
        logger.info(f"[SUMMARY] Đã chuyển trạng thái Document ID={document_id} sang 'processing'.")

        try:
            if not os.path.exists(doc_record.file_path):
                logger.error(
                    f"[SUMMARY] Thất bại: File vật lý không tồn tại trên ổ cứng tại: {doc_record.file_path}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File tài liệu vật lý không tồn tại trên server.",
                )

            # 3. Mở file bằng PyMuPDF và kiểm tra giới hạn trang (Tính năng PRO)
            pdf_doc = fitz.open(doc_record.file_path)
            total_pages = len(pdf_doc)
            logger.info(
                f"[SUMMARY] Mở file bằng PyMuPDF thành công. Tổng số trang: {total_pages} trang."
            )

            max_allowed_pages = 15
            if total_pages > max_allowed_pages:
                doc_record.status = "failed"
                self.db.commit()
                logger.warning(
                    f"[SUMMARY] Bị chặn (Giới hạn PRO): File có {total_pages} trang, vượt quá mức cho phép {max_allowed_pages} trang."
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tài liệu quá dài ({total_pages} trang). Vui lòng nâng cấp lên gói PRO để xử lý file vượt quá {max_allowed_pages} trang!",
                )

            # 4. Trích xuất text thô từ PDF
            full_text = ""
            for page_num, page in enumerate(pdf_doc, start=1):
                full_text += page.get_text()

            pdf_doc.close()
            logger.info(
                f"[SUMMARY] Đã hoàn thành trích xuất {len(full_text)} ký tự văn bản thô từ file PDF."
            )

            if not full_text.strip():
                logger.warning(
                    f"[SUMMARY] Thất bại: File Document ID={document_id} trích xuất ra text rỗng (Có thể là ảnh quét hoàn toàn)."
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Không thể trích xuất văn bản (PDF trống hoặc là file ảnh quét).",
                )

            # 5. Gọi AI Dummy tóm tắt văn bản
            logger.info(
                "[SUMMARY] Đang chuyển tiếp dữ liệu chữ thô sang AI Service để tiến hành tóm tắt..."
            )
            ai_summary = AISummarizerService.generate_summary(full_text)
            logger.info("[SUMMARY] AI Service đã phản hồi bản tóm tắt thành công.")

            # 6. Cập nhật kết quả vào MySQL để lưu lịch sử
            doc_record.parsed_content = full_text
            doc_record.summary_content = ai_summary
            doc_record.status = "completed"

            self.db.commit()
            self.db.refresh(doc_record)

            logger.info(
                f"[SUMMARY] Đã cập nhật xong text thô + nội dung tóm tắt vào DB. Đổi trạng thái Document ID={document_id} thành 'completed'."
            )
            return doc_record

        except HTTPException as http_e:
            # Re-raise lỗi HTTP chủ động (lỗi file trống, lỗi quá trang)
            raise http_e
        except Exception as e:
            doc_record.status = "failed"
            self.db.commit()
            logger.error(f"[SUMMARY] LỖI CRASH KHI GỌI AI HOẶC PARSE FILE: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi nghiêm trọng khi xử lý AI: {str(e)}",
            )
