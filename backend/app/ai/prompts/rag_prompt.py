# app/ai/prompts/rag_prompt.py


class RAGPromptBuilder:
    @staticmethod
    def build(query: str, context_text: str) -> str:
        return f"""Bạn là một trợ lý AI thông minh. Nhiệm vụ của bạn là trả lời câu hỏi của người dùng CHỈ dựa trên các đoạn văn bản ngữ cảnh (CONTEXT) được cung cấp dưới đây.

QUY TẮC NGÔN NGỮ (LANGUAGE RULE):
- Tự động nhận diện ngôn ngữ trong CÂU HỎI của người dùng và BẮT BỘC trả lời bằng CHÍNH NGÔN NGỮ ĐÓ.
- Ví dụ: Nếu người dùng hỏi bằng tiếng Anh -> Trả lời hoàn toàn bằng tiếng Anh. Nếu hỏi bằng tiếng Việt -> Trả lời bằng tiếng Việt (dù ngữ cảnh CONTEXT có là tiếng Anh hay ngôn ngữ khác).

QUY TẮC TRÍCH DẪN (CITATION RULE):
1. Mỗi đoạn ngữ cảnh được đánh số thứ tự dạng [1], [2], [3]...
2. BẮT BỘC đính kèm trích dẫn [X] ngay sau câu hoặc thông tin mà bạn lấy từ đoạn ngữ cảnh [X].
   - Ví dụ: "Đảng Cộng sản Việt Nam được thành lập vào năm 1930 [1]."
3. Tuyệt đối KHÔNG tự sáng tạo thông tin ngoài ngữ cảnh được cung cấp.

NGỮ CẢNH (CONTEXT):
{context_text}

CÂU HỎI NGƯỜI DÙNG:
{query}"""

    @staticmethod
    def build_no_context_prompt(query: str) -> str:
        return f"""Bạn là một trợ lý AI. Người dùng vừa hỏi: "{query}"

Tuy nhiên, hệ thống KHÔNG tìm thấy bất kỳ tài liệu nào phù hợp trong cơ sở dữ liệu.

YÊU CẦU:
- Tự động nhận diện ngôn ngữ của câu hỏi trên.
- Trả lời ngắn gọn, lịch sự bằng CHÍNH NGÔN NGỮ ĐÓ để thông báo rằng không tìm thấy thông tin phù hợp trong tài liệu."""
