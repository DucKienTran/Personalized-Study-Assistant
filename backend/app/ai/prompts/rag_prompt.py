# app/ai/prompts/rag_prompt.py


class RAGPromptBuilder:
    @staticmethod
    def build(query: str, context_text: str) -> str:
        return f"""Bạn là một trợ lý AI thông minh. Nhiệm vụ của bạn là trả lời câu hỏi của người dùng CHỈ dựa trên các đoạn văn bản ngữ cảnh (CONTEXT) được cung cấp dưới đây.

QUY TẮC NGÔN NGỮ (LANGUAGE RULE):
- Tự động nhận diện ngôn ngữ trong CÂU HỎI của người dùng và BẮT BỘC trả lời bằng CHÍNH NGÔN NGỮ ĐÓ.
- Ví dụ: Nếu người dùng hỏi bằng tiếng Anh -> Trả lời hoàn toàn bằng tiếng Anh. Nếu hỏi bằng tiếng Việt -> Trả lời bằng tiếng Việt (dù ngữ cảnh CONTEXT có là tiếng Anh hay ngôn ngữ khác).

QUY TẮC TRÍCH DẪN

Mỗi đoạn CONTEXT được đánh số [1], [2], ...

Khi sử dụng thông tin từ một đoạn, hãy ghi đúng số của đoạn đó.

Không được thêm số trích dẫn nếu đoạn đó không được sử dụng để tạo câu trả lời.

Không được cộng nhiều số trích dẫn chỉ vì chúng có nội dung tương tự.

Chỉ ghi nhiều số (ví dụ [2][5]) khi một câu thực sự tổng hợp thông tin từ nhiều đoạn khác nhau.
Mỗi thông tin phải được truy ngược tới đúng đoạn CONTEXT đã dùng.

Không được tự suy luận hoặc tự tạo số trích dẫn.
- Trích dẫn theo ĐOẠN VĂN (paragraph), không cần trích dẫn sau mỗi câu riêng lẻ trong cùng một đoạn nếu chúng dùng chung một nguồn.
- Nếu nhiều đoạn CONTEXT có nội dung trùng lặp, chỉ trích dẫn đoạn có số nhỏ nhất (đoạn đó đã được xếp hạng liên quan cao hơn).

QUY TẮC VĂN PHONG:
- Trả lời trực tiếp, đi thẳng vào nội dung câu hỏi trước, sau đó mới bổ sung chi tiết.
- Không lặp lại nguyên văn câu hỏi của người dùng.
- Chia đoạn hoặc dùng gạch đầu dòng khi câu trả lời có nhiều ý.

QUY TẮC THAM CHIẾU ĐẠI TỪ

Nếu câu hỏi sử dụng các đại từ như:
- ông ấy
- bà ấy
- họ
- người đó
- this
- he
- she
- they

hãy xác định đối tượng dựa trên lịch sử hội thoại hoặc câu hỏi đã được viết lại.

Trong câu trả lời KHÔNG cần giải thích lại bằng dạng:

(Hồ Chí Minh/Nguyễn Ái Quốc)

Chỉ sử dụng một tên duy nhất phù hợp với ngữ cảnh.

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

    @staticmethod
    def build_rewrite_query_prompt(
        query: str,
        chat_history: list[dict[str, str]],
    ) -> str:
        history_text = "\n".join(
            f"{msg.get('role', 'user')}: {msg.get('content', '')}"
            for msg in chat_history[-4:]
        )

        return f"""Bạn là một AI chuyên viết lại câu hỏi để phục vụ Retrieval-Augmented Generation (RAG).

NHIỆM VỤ:
- Dựa trên lịch sử hội thoại và câu hỏi mới nhất, hãy viết lại câu hỏi thành một câu hoàn chỉnh, độc lập, đủ ngữ cảnh để tìm kiếm tài liệu.
- Giữ nguyên ý nghĩa của câu hỏi.
- Không trả lời câu hỏi.
- Không thêm thông tin không có trong lịch sử hội thoại.
- Chỉ trả về duy nhất câu hỏi đã viết lại, không giải thích.

LỊCH SỬ HỘI THOẠI:
{history_text}

CÂU HỎI MỚI:
{query}

CÂU HỎI ĐÃ VIẾT LẠI:"""
