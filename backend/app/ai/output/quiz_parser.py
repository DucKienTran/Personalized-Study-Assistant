import json
import re
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class QuizQuestionSchema(BaseModel):
    question_text: str
    question_type: str
    options: Optional[List[str]] = None
    correct_answer: Optional[Union[str, List[str], bool]] = None
    explanations: Optional[Dict[str, str]] = None
    points: int = Field(default=1, ge=1)
    hint: Optional[str] = None

    @field_validator("question_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        # Danh sách 6 loại Quiz
        allowed = [
            "multiple_choice",
            "multiple_response",
            "true_false",
            "fill_blank",
            "short_answer",
            "essay",
        ]
        if v not in allowed:
            raise ValueError(f"Loại câu hỏi '{v}' không hợp lệ. Phải thuộc: {allowed}")
        return v

    @model_validator(mode="after")
    def validate_logic_by_type(self) -> "QuizQuestionSchema":
        """
        Kiểm tra chéo (Cross-validation) dữ liệu nhằm bọc lót các trường hợp AI sinh lỗi cấu trúc nhỏ,
        đảm bảo dữ liệu đầu ra chuẩn chỉnh để lưu vào Database.
        """
        q_type = self.question_type
        ans = self.correct_answer

        # Dạng Trắc nghiệm 1 đáp án đúng
        if q_type == "multiple_choice":
            if not self.options or len(self.options) < 2:
                raise ValueError(
                    f"Câu '{self.question_text[:20]}...': Trắc nghiệm phải có >= 2 options."
                )
            if not isinstance(ans, str):
                raise ValueError(
                    "Trắc nghiệm multiple_choice correct_answer phải là chuỗi (VD: 'A')."
                )

        # Dạng Trắc nghiệm NHIỀU đáp án đúng
        elif q_type == "multiple_response":
            if not self.options or len(self.options) < 2:
                raise ValueError(
                    f"Câu '{self.question_text[:20]}...': Trắc nghiệm nhiều đáp án phải có >= 2 options."
                )
            if isinstance(ans, str):
                # Phòng hờ AI lỡ tay trả về chuỗi cách nhau bằng dấu phẩy "A,C" thay vì mảng
                self.correct_answer = [x.strip() for x in ans.split(",") if x.strip()]
            elif not isinstance(self.correct_answer, list):
                raise ValueError(
                    "Trắc nghiệm multiple_response correct_answer phải là một mảng (List[str])."
                )

        # Dạng Đúng / Sai
        elif q_type == "true_false":
            if not isinstance(ans, bool):
                if str(ans).lower() in ["true", "1"]:
                    self.correct_answer = True
                elif str(ans).lower() in ["false", "0"]:
                    self.correct_answer = False
                else:
                    raise ValueError(
                        "true_false correct_answer bắt buộc phải là Boolean (True/False)."
                    )

        # Dạng Điền vào chỗ trống
        elif q_type == "fill_blank":
            if ans is None:
                raise ValueError("fill_blank không được để trống correct_answer.")
            if isinstance(ans, str):
                self.correct_answer = [ans]
            elif not isinstance(self.correct_answer, list):
                raise ValueError(
                    "fill_blank correct_answer phải là mảng chứa các đáp án hợp lệ (List[str])."
                )

        # Dạng Trả lời ngắn
        elif q_type == "short_answer":
            if ans is None:
                raise ValueError("short_answer không được để trống correct_answer.")
            if isinstance(ans, list):
                if len(ans) > 0:
                    self.correct_answer = str(ans[0]).strip()
                else:
                    raise ValueError(
                        "short_answer mảng correct_answer không được để trống phần tử."
                    )
            else:
                self.correct_answer = str(ans).strip()

        # Tự luận, tạm thời chưa có
        elif q_type == "essay":
            pass

        return self


class QuizParser:
    @staticmethod
    def parse_quiz_response(raw_text: str) -> List[dict]:
        """
        Làm sạch markdown code block, chuyển đổi text sang JSON array và validate qua Pydantic.
        """
        clean_text = raw_text.strip()

        backticks = chr(96) * 3
        pattern = f"{backticks}(?:json)?\\s*([\\s\\S]*?)\\s*{backticks}"

        match = re.search(pattern, clean_text)
        if match:
            clean_text = match.group(1).strip()

        try:
            parsed_json = json.loads(clean_text)

            if isinstance(parsed_json, dict) and "questions" in parsed_json:
                parsed_json = parsed_json["questions"]
            elif isinstance(parsed_json, dict):
                parsed_json = [parsed_json]

            if not isinstance(parsed_json, list):
                raise ValueError("Dữ liệu gốc từ AI không quy về được định dạng mảng (Array JSON).")

            validated_questions = []
            for item in parsed_json:
                validated_item = QuizQuestionSchema(**item)
                validated_questions.append(validated_item.model_dump())

            return validated_questions

        except json.JSONDecodeError as je:
            raise ValueError(
                f"LLM trả về chuỗi JSON lỗi cấu trúc, không thể thực hiện ép kiểu. Chi tiết: {str(je)}"
            )
        except Exception as e:
            raise ValueError(
                f"Dữ liệu từ AI sinh ra vi phạm nghiêm trọng Schema an toàn hệ thống: {str(e)}"
            )
