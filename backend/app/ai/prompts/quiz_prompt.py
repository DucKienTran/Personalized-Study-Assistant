from typing import List


class QuizPrompt:
    @staticmethod
    def generate_quiz_prompt(
        content_raw: str,
        question_types: List[str],
        total_questions: int,
        level: str
    ) -> str:
        """
        Xây dựng hệ thống Prompt ép AI trả về cấu trúc đề thi hỗn hợp gồm 6 dạng JSON thuần.
        """
        # Ánh xạ thông tin hiển thị loại câu hỏi sang tiếng Việt trong prompt để AI hiểu ngữ cảnh
        type_mapping = {
            "multiple_choice": "Trắc nghiệm 1 lựa chọn đúng (multiple_choice)",
            "multiple_response": "Trắc nghiệm NHIỀU lựa chọn đúng (multiple_response)",
            "true_false": "Đúng/Sai (true_false)",
            "fill_blank": "Điền vào chỗ trống ngữ cảnh (fill_blank)",
            "short_answer": "Trả lời ngắn/Điền số chuẩn hóa (short_answer)",
            "essay": "Tự luận/Câu hỏi mở (essay)"
        }
        requested_types = [type_mapping.get(t, t) for t in question_types]
        requested_types_str = ", ".join(requested_types)

        return f"""Bạn là một chuyên gia khảo thí và AI giáo dục cao cấp. Nhiệm vụ của bạn là đọc kỹ tài liệu thô được cung cấp dưới đây và biên soạn một bộ câu hỏi đạt chuẩn giáo dục dựa trên các yêu cầu sau:

--- YÊU CẦU BỘ ĐỀ CHÚNG TÔI CẦN ---
1. Tổng số câu hỏi: {total_questions} câu.
2. Độ khó mục tiêu: Mức độ "{level}" (Nhận biết/Thông hiểu/Vận dụng/Vận dụng cao).
3. Các dạng câu hỏi cần phân bổ: {requested_types_str}.
4. Mỗi câu hỏi cần được gán trọng số điểm (`points`) tương ứng với độ khó của chính câu hỏi đó (Ví dụ: Câu nhận biết = 1 điểm, câu vận dụng cao = 2 hoặc 3 điểm).

--- NỘI DUNG TÀI LIỆU NGUỒN ---
{content_raw}

--- QUY TẮC ĐỊNH DẠNG CẤU TRÚC JSON ---
Bạn BẮT BUỘC phải trả về dữ liệu dạng JSON Array thuần túy, tuyệt đối không chèn thêm bất kỳ chữ giải thích nào ngoài khối JSON. Mỗi object câu hỏi trong mảng phải có cấu trúc chính xác theo từng loại như sau:

1. Dạng câu hỏi "multiple_choice" (Trắc nghiệm 1 đáp án đúng):
{{
  "question_text": "Chuỗi văn bản câu hỏi...",
  "question_type": "multiple_choice", 
  "options": ["A. Lựa chọn một", "B. Lựa chọn hai", "C. Lựa chọn ba", "D. Lựa chọn bốn"],
  "correct_answer": "A",
  "explanations": {{
    "A": "Giải thích tại sao đáp án A đúng...",
    "B": "Giải thích tại sao đáp án B sai...",
    "C": "Giải thích tại sao C sai...",
    "D": "Giải thích tại sao D sai..."
  }},
  "points": 1,
  "hint": "Gợi ý làm bài ngắn gọn (nếu có)"
}}

2. Dạng câu hỏi "multiple_response" (Trắc nghiệm NHIỀU đáp án đúng):
{{
  "question_text": "Chuỗi văn bản câu hỏi (Yêu cầu người học chọn TẤT CẢ các đáp án đúng)...",
  "question_type": "multiple_response", 
  "options": ["A. Phương án một", "B. Phương án hai", "C. Phương án ba", "D. Phương án bốn"],
  "correct_answer": ["A", "C"],
  "explanations": {{
    "A": "Giải thích tại sao phương án A đúng...",
    "B": "Giải thích tại sao phương án B sai...",
    "C": "Giải thích tại sao phương án C đúng...",
    "D": "Giải thích tại sao phương án D sai..."
  }},
  "points": 2,
  "hint": "Lưu ý câu hỏi này có nhiều hơn một đáp án đúng."
}}

3. Dạng câu hỏi "true_false" (Đúng / Sai):
{{
  "question_text": "Chuỗi văn bản mệnh đề cần xác định tính đúng sai...",
  "question_type": "true_false", 
  "options": null,
  "correct_answer": true,
  "explanations": {{
    "general": "Giải thích tường tận tại sao mệnh đề này lại Đúng hoặc Sai dựa trên tài liệu..."
  }},
  "points": 1,
  "hint": null
}}

4. Dạng câu hỏi "fill_blank" (Điền khuyết bằng text):
{{
  "question_text": "Chuỗi văn bản chứa chỗ trống, sử dụng ký tự [blank] để đánh dấu vị trí cần điền.",
  "question_type": "fill_blank",
  "options": null,
  "correct_answer": ["đáp án đúng nhất", "đáp án biến thể chấp nhận được"],
  "explanations": {{
    "general": "Giải thích tại sao từ/cụm từ này lại phù hợp vào ngữ cảnh của câu..."
  }},
  "points": 1,
  "hint": "Gợi ý từ loại hoặc ký tự đầu tiên"
}}

5. Dạng câu hỏi "short_answer" (Trả lời ngắn - Điền số chuẩn hóa, thích hợp cho bài tập tính toán):
{{
  "question_text": "Nội dung bài tập tính toán yêu cầu đưa ra kết quả bằng số cụ thể...",
  "question_type": "short_answer",
  "options": null,
  "correct_answer": "3.14",
  "explanations": {{
    "general": "Trình bày tóm tắt các bước giải toán, công thức áp dụng để ra được đáp số."
  }},
  "points": 2,
  "hint": "Lấy giá trị xấp xỉ đến 2 chữ số thập phân hoặc điền số nguyên chuẩn hóa (VD: 3.14, -12, 0.5)"
}}

6. Dạng câu hỏi "essay" (Tự luận / Câu hỏi mở rộng):
{{
  "question_text": "Nội dung câu hỏi tự luận yêu cầu lập luận, phân tích sâu...",
  "question_type": "essay",
  "options": null,
  "correct_answer": ["Ý chính 1 cần đạt", "Ý chính 2 cần đạt", "Tiêu chí chấm điểm (Rubric)..."],
  "explanations": null,
  "points": 3,
  "hint": "Gợi ý các hướng tiếp cận khía cạnh luận điểm"
}}

Hãy đảm bảo rằng mảng JSON chứa chính xác {total_questions} câu hỏi với các định dạng tương ứng như trên. Hãy bắt đầu sinh dữ liệu JSON ngay dưới đây:"""