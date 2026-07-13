import json
import re
from typing import ClassVar, Dict, List, Optional, Union

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator


class QuizQuestionSchema(BaseModel):
    ALLOWED_TYPES: ClassVar[set[str]] = {
        "multiple_choice",
        "multiple_response",
        "true_false",
        "fill_blank",
        "short_answer",
        "essay",
    }

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
        if v not in cls.ALLOWED_TYPES:
            raise ValueError(
                f"Loại câu hỏi '{v}' không hợp lệ. Phải thuộc: {cls.ALLOWED_TYPES}"
            )
        return v

    @model_validator(mode="after")
    def validate_logic_by_type(self) -> "QuizQuestionSchema":
        q_type = self.question_type
        ans = self.correct_answer

        if q_type == "multiple_choice":
            if not self.options or len(self.options) < 2:
                raise ValueError(
                    f"Câu '{self.question_text[:20]}...': Trắc nghiệm phải có >= 2 options."
                )
            if not isinstance(ans, str):
                raise ValueError(
                    "Trắc nghiệm multiple_choice correct_answer phải là chuỗi (VD: 'A')."
                )

            valid_labels = {opt.split(".")[0].strip() for opt in self.options}
            if ans.strip() not in valid_labels:
                raise ValueError(
                    f"Câu '{self.question_text[:20]}...': correct_answer='{ans}' "
                    f"không khớp với bất kỳ nhãn nào trong options ({valid_labels})."
                )

        elif q_type == "multiple_response":
            if not self.options or len(self.options) < 2:
                raise ValueError(
                    f"Câu '{self.question_text[:20]}...': Trắc nghiệm nhiều đáp án phải có >= 2 options."
                )
            if isinstance(ans, str):
                self.correct_answer = [x.strip() for x in ans.split(",") if x.strip()]
            elif not isinstance(self.correct_answer, list):
                raise ValueError(
                    "Trắc nghiệm multiple_response correct_answer phải là một mảng (List[str])."
                )

            valid_labels = {opt.split(".")[0].strip() for opt in self.options}
            invalid = [a for a in self.correct_answer if a.strip() not in valid_labels]
            if invalid:
                raise ValueError(
                    f"Câu '{self.question_text[:20]}...': các đáp án {invalid} "
                    f"không khớp với nhãn nào trong options ({valid_labels})."
                )

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

        elif q_type == "fill_blank":
            if ans is None:
                raise ValueError("fill_blank không được để trống correct_answer.")
            if isinstance(ans, str):
                self.correct_answer = [ans.strip()]
            elif isinstance(ans, list):
                self.correct_answer = [str(a).strip() for a in ans]
            else:
                raise ValueError(
                    "fill_blank correct_answer phải là mảng chứa các đáp án hợp lệ (List[str])."
                )

        elif q_type == "short_answer":
            if ans is None:
                raise ValueError("short_answer không được để trống correct_answer.")
            if isinstance(ans, list):
                if len(ans) == 0:
                    raise ValueError(
                        "short_answer mảng correct_answer không được để trống phần tử."
                    )
                self.correct_answer = str(ans[0]).strip()
            else:
                self.correct_answer = str(ans).strip()

        elif q_type == "essay":
            pass

        return self


class QuizParser:
    @staticmethod
    def parse_quiz_response(raw_text: str) -> List[dict]:
        clean_text = raw_text.strip()

        backticks = chr(96) * 3
        pattern = f"{backticks}(?:json)?\\s*([\\s\\S]*?)\\s*{backticks}"

        match = re.search(pattern, clean_text)
        if match:
            clean_text = match.group(1).strip()

        try:
            parsed_json = json.loads(clean_text)
        except json.JSONDecodeError as je:
            raise ValueError(
                f"LLM trả về chuỗi JSON lỗi cấu trúc, không thể thực hiện ép kiểu. Chi tiết: {str(je)}"
            )

        if isinstance(parsed_json, dict) and "questions" in parsed_json:
            quiz_title = parsed_json.get(
                "quiz_title",
                "Đề thi chưa đặt tên",
            )

            questions = parsed_json["questions"]

        else:
            quiz_title = "Đề thi chưa đặt tên"

            if isinstance(parsed_json, list):
                questions = parsed_json
            else:
                questions = [parsed_json]

        if not isinstance(questions, list):
            raise ValueError(
                "Dữ liệu gốc từ AI không quy về được định dạng mảng (Array JSON)."
            )

        validated_questions = []
        for idx, item in enumerate(questions):
            try:
                validated_item = QuizQuestionSchema(**item)
                validated_questions.append(validated_item.model_dump())
            except ValidationError as ve:
                raise ValueError(f"Câu hỏi thứ {idx + 1} vi phạm schema: {ve}")

        return {
            "quiz_title": quiz_title,
            "questions": validated_questions,
        }
