from typing import List, Optional


class QuizPromptBuilder:
    """
    Sinh prompt cho việc tạo đề thi bằng AI, tách 2 nhánh: simple / custom.
    Nguyên tắc: KHÔNG parse custom_instruction bằng code — để LLM tự hiểu ngôn ngữ tự nhiên,
    backend chỉ ép ràng buộc CỨNG (tổng điểm, JSON schema, chống bịa nội dung).
    """

    _JSON_SCHEMA_RULES = """
--- QUY TẮC ĐỊNH DẠNG CẤU TRÚC JSON (BẮT BUỘC) ---
Trả về DUY NHẤT một JSON hợp lệ theo đúng cấu trúc sau:

{
  "quiz_title": "Tên bộ đề ngắn gọn",
  "questions": [
    {
      ...
    }
  ]
}

Yêu cầu:
- quiz_title: dưới 12 từ.
- Phản ánh chủ đề chính của tài liệu.
- Không dùng tên chung chung như "Đề thi", "Quiz", "Bài kiểm tra".
nội dung tài liệu nguồn — KHÔNG dùng tên chung chung như "Đề thi", "Bài kiểm tra".
Ví dụ tốt: "Kiểm tra chương 2: Cấu trúc dữ liệu và giải thuật"
Nội dung trả về KHÔNG bọc trong markdown code fence.
KHÔNG thêm bất kỳ chữ giải thích nào trước/sau khối JSON.

Mỗi object câu hỏi PHẢI có đúng các field sau, tuỳ theo question_type:

1. "multiple_choice":
{
  "question_text": "...",
  "question_type": "multiple_choice",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "correct_answer": "A",
  "explanations": {"A": "...", "B": "...", "C": "...", "D": "..."},
  "points": 4,
  "hint": "..."
}

2. "multiple_response" (nhiều đáp án đúng):
{
  "question_text": "...",
  "question_type": "multiple_response",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "correct_answer": ["A", "C"],
  "explanations": {"A": "...", "B": "...", "C": "...", "D": "..."},
  "points": 4,
  "hint": "..."
}

3. "true_false":
{
  "question_text": "...",
  "question_type": "true_false",
  "options": null,
  "correct_answer": true,
  "explanations": {"general": "..."},
  "points": 2,
  "hint": "..."
}

4. "fill_blank":
{
  "question_text": "Câu chứa [blank] cần điền.",
  "question_type": "fill_blank",
  "options": null,
  "correct_answer": ["đáp án đúng 1", "cách viết chấp nhận được 2"],
  "explanations": {"general": "..."},
  "points": 3,
  "hint": "..."
}

5. "short_answer" (trả lời ngắn bằng số/ký hiệu, kiểu đề thi Toán):
{
  "question_text": "...",
  "question_type": "short_answer",
  "options": null,
  "correct_answer": "3.14",
  "explanations": {"general": "..."},
  "points": 3,
  "hint": "..."
}
LƯU Ý: correct_answer PHẢI có độ dài TỐI ĐA 4 ký tự (tính cả dấu trừ và dấu thập phân
nếu có). Chỉ được sinh câu hỏi short_answer nếu đáp án đúng có thể biểu diễn gọn (kể cả 
kết quả chính xác hay làm tròn) trong 4 ký tự (ví dụ: "12", "-5", "3.14", "0.5"). 
KHÔNG sinh short_answer nếu đáp án tự nhiêndài hơn — trong trường hợp đó, đổi câu hỏi sang 
dạng khác (fill_blank/multiple_choice/...) hoặc bỏ câu đó.

6. "essay":
{
  "question_text": "...",
  "question_type": "essay",
  "options": null,
  "correct_answer": ["Ý chính 1 cần có", "Ý chính 2 cần có", "Tiêu chí chấm điểm..."],
  "explanations": null,
  "points": 5,
  "hint": "..."
}
"""

    _HARD_CONSTRAINTS = """
--- RÀNG BUỘC BẮT BUỘC PHẢI TUÂN THỦ ---
1. Tổng điểm (points) của TẤT CẢ câu hỏi PHẢI cộng lại CHÍNH XÁC bằng: {target_total_points}.
   Đây là ràng buộc cứng, không được sai lệch dù chỉ 1 điểm.
2. Sinh đúng {total_questions} câu nếu có thể. Nếu tài liệu nguồn KHÔNG đủ nội dung để
   sinh đủ số câu có chất lượng, hãy sinh ÍT HƠN thay vì bịa thêm nội dung không có
   trong tài liệu. TUYỆT ĐỐI KHÔNG sinh NHIỀU HƠN số câu yêu cầu.
3. Không được tự chế đề, câu hỏi bịa, hoặc câu hỏi mơ hồ không có căn cứ.
4. Không được bịa đặt sự kiện/số liệu nằm ngoài nội dung tài liệu nguồn được cung cấp.
5. Mọi đáp án và giải thích PHẢI có căn cứ trực tiếp từ nội dung tài liệu nguồn.
6. Mỗi câu hỏi PHẢI kiểm tra một điểm kiến thức RIÊNG BIỆT. Không hỏi lại cùng 1 khái
   niệm bằng cách diễn đạt khác nhau (trừ khi người dùng yêu cầu rõ điều này).
7. KHÔNG được để lộ đáp án ngay trong nội dung câu hỏi (ví dụ: không mô tả định nghĩa
   đầy đủ của khái niệm rồi hỏi lại chính khái niệm đó).

"""

    @staticmethod
    def _build_source_and_schema(
        content_raw: str, target_total_points: int, total_questions: int
    ) -> str:
        constraints = QuizPromptBuilder._HARD_CONSTRAINTS.format(
            target_total_points=target_total_points, total_questions=total_questions
        )
        return f"""
--- NỘI DUNG TÀI LIỆU NGUỒN ---
{content_raw}
{constraints}
{QuizPromptBuilder._JSON_SCHEMA_RULES}

Hãy bắt đầu sinh dữ liệu JSON ngay dưới đây:"""

    @staticmethod
    def build_simple(
        content_raw: str,
        total_questions: int,
        difficulty: str,  # "easy" | "medium" | "hard" | "mixed"
        question_types: List[str],
        target_total_points: int,
    ) -> str:
        difficulty_instruction = {
            "easy": "Toàn bộ câu hỏi ở mức độ Nhận biết/Dễ.",
            "medium": "Toàn bộ câu hỏi ở mức độ Thông hiểu/Trung bình.",
            "hard": "Toàn bộ câu hỏi ở mức độ Vận dụng/Vận dụng cao/Khó.",
            "mixed": (
                "Trộn độ khó theo tỉ lệ: 40% Dễ (Nhận biết), 40% Trung bình (Thông hiểu), "
                "20% Khó (Vận dụng/Vận dụng cao). KHÔNG gom nhóm các câu cùng độ khó lại "
                "gần nhau — trộn ngẫu nhiên thứ tự trong toàn bộ đề."
            ),
        }.get(
            difficulty,
            "Độ khó trung bình, phù hợp trình độ phổ thông/đại học đại cương.",
        )

        types_instruction = (
            f"Các dạng câu hỏi cần dùng: {', '.join(question_types)}.\n"
            f"Nếu người dùng không chỉ định tỉ lệ cụ thể giữa các dạng, hãy PHÂN BỔ ĐỀU "
            f"nhất có thể giữa {len(question_types)} dạng trên (ví dụ 15 câu, 3 dạng → 5-5-5; "
            f"nếu chia không hết, phần dư phân bổ thêm vào dạng đầu tiên)."
        )

        header = f"""Bạn là chuyên gia khảo thí AI. Biên soạn bộ đề thi dựa trên tài liệu nguồn dưới đây theo cấu hình:

--- CẤU HÌNH (SIMPLE MODE) ---
Số câu hỏi mong muốn: {total_questions}
Độ khó: {difficulty_instruction}
{types_instruction}
"""
        return header + QuizPromptBuilder._build_source_and_schema(
            content_raw, target_total_points, total_questions
        )

    @staticmethod
    def build_custom(
        content_raw: str,
        total_questions: int,
        target_total_points: int,
        custom_instruction: str,
        question_types: Optional[List[str]] = None,
        difficulty: Optional[str] = None,
    ) -> str:
        default_types = (
            f"Mặc định nếu không được chỉ định trong yêu cầu: {', '.join(question_types)}."
            if question_types
            else ""
        )
        default_difficulty = (
            f"Độ khó mặc định nếu không được chỉ định trong yêu cầu: {difficulty}."
            if difficulty
            else ""
        )

        header = f"""Bạn là chuyên gia khảo thí AI. Biên soạn bộ đề thi dựa trên tài liệu nguồn dưới đây.

--- YÊU CẦU TUỲ CHỈNH TỪ NGƯỜI DÙNG (ƯU TIÊN TUYỆT ĐỐI) ---
{custom_instruction}

--- THỨ TỰ ƯU TIÊN KHI CÓ THÔNG TIN THIẾU HOẶC MÂU THUẪN ---
Ưu tiên 1: Tuân theo ĐÚNG yêu cầu tuỳ chỉnh ở trên (loại câu hỏi, tỉ lệ %, độ khó, thứ tự sắp xếp...).
Ưu tiên 2: Với bất kỳ thuộc tính nào yêu cầu tuỳ chỉnh KHÔNG đề cập tới, dùng cấu hình mặc định sau:
{default_types}
{default_difficulty}
Số câu hỏi mong muốn (nếu yêu cầu tuỳ chỉnh không nói rõ số lượng): {total_questions}

Nếu yêu cầu tuỳ chỉnh và cấu hình mặc định MÂU THUẪN nhau, LUÔN ưu tiên yêu cầu tuỳ chỉnh.
"""
        return header + QuizPromptBuilder._build_source_and_schema(
            content_raw, target_total_points, total_questions
        )

    @staticmethod
    def build(
        generation_mode: str,
        content_raw: str,
        total_questions: int,
        target_total_points: int,
        question_types: Optional[List[str]] = None,
        difficulty: Optional[str] = None,
        custom_instruction: Optional[str] = None,
    ) -> str:
        if generation_mode == "custom":
            return QuizPromptBuilder.build_custom(
                content_raw=content_raw,
                total_questions=total_questions,
                target_total_points=target_total_points,
                custom_instruction=custom_instruction or "Không có yêu cầu bổ sung.",
                question_types=question_types,
                difficulty=difficulty,
            )

        return QuizPromptBuilder.build_simple(
            content_raw=content_raw,
            total_questions=total_questions,
            difficulty=difficulty or "medium",
            question_types=question_types or ["multiple_choice"],
            target_total_points=target_total_points,
        )
