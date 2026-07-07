class AISummarizerService:
    @staticmethod
    def generate_summary(text: str) -> str:
        """
        Hàm giả lập gọi AI để tóm tắt văn bản.
        Sau này bạn sẽ tích hợp LangChain/Mastra Agent hoặc gọi trực tiếp API ở đây.
        """
        # Trích xuất một đoạn ngắn của văn bản gốc để demo cảm giác AI đang đọc thật
        preview = text[:150].strip().replace("\n", " ") if text else "Không có dữ liệu"

        return (
            "###  BẢN TÓM TẮT TÀI LIỆU (AI DEMO VERSION)\n\n"
            f'1. **Tổng quan tài liệu:** Hệ thống đã đọc nội dung bắt đầu bằng: *"{preview}..."*\n\n'
            "2. **Các luận điểm cốt lõi tìm thấy:**\n"
            "   - **Luận điểm 1:** Tài liệu cung cấp nền tảng kiến thức quan trọng phục vụ cho việc sinh bộ câu hỏi kiểm tra tự động.\n"
            "   - **Luận điểm 2:** Cấu trúc nội dung được tổ chức mạch lạc, phù hợp để triển khai cơ chế RAG (Retrieval-Augmented Generation).\n\n"
            "3. **Kết luận từ AI:** Đây là kết quả tóm tắt chạy hoàn toàn đồng bộ, đảm bảo dữ liệu lịch sử đã được lưu lại hệ thống thành công."
        )
