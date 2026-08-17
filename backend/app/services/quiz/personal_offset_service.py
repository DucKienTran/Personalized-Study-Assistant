from typing import Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.constants.quiz_profile import (
    DEFAULT_QUIZ_PROFILE,
    QUIZ_PROFILE_BOUNDS,
    QUIZ_PROFILE_FIELDS,
    SMOOTHING_FACTOR,
)
from app.models.quiz_offset_model import UserQuizProfileOffset
from app.schemas.quiz_profile_schema import MergedQuizProfileOut


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


class PersonalOffsetService:
    """
    Quản lý personal offset của user cho quiz profile.

    Chỉ 3 việc:
    - get_or_create_offset: lấy dòng offset của user, tạo mới nếu chưa có
    - get_merged_profile: DEFAULT_QUIZ_PROFILE + offset, đã clamp -> dùng
      cho QuizPromptBuilder
    - apply_delta: cộng delta (đã smoothing) vào offset hiện tại, clamp,
      lưu lại

    KHÔNG orchestrate feedback (preset + AI delta) — việc đó nằm ở
    feedback_service.py.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_offset(self, user_id: int) -> UserQuizProfileOffset:
        stmt = select(UserQuizProfileOffset).where(UserQuizProfileOffset.user_id == user_id)
        result = self.db.execute(stmt)
        offset = result.scalar_one_or_none()

        if offset is None:
            offset = UserQuizProfileOffset(user_id=user_id)
            self.db.add(offset)
            self.db.commit()
            self.db.refresh(offset)
        return offset

    def get_merged_profile(self, user_id: int) -> MergedQuizProfileOut:
        offset = self.get_or_create_offset(user_id)

        merged: Dict[str, float] = {}
        for field in QUIZ_PROFILE_FIELDS:
            default_value = DEFAULT_QUIZ_PROFILE[field]
            offset_value = getattr(offset, f"{field}_offset")
            bounds = QUIZ_PROFILE_BOUNDS[field]
            # Clamp phòng hờ: nếu sau này đổi DEFAULT_QUIZ_PROFILE mà
            # offset cũ (đã lưu trước đó) đẩy merged value vượt khoảng
            # hợp lệ, vẫn phải clamp lại ở đây chứ không tin offset đã
            # luôn nằm trong khoảng đúng.
            merged[field] = _clamp(default_value + offset_value, bounds["min"], bounds["max"])

        return MergedQuizProfileOut(**merged)

    def apply_delta(self, user_id: int, delta: Dict[str, float]) -> UserQuizProfileOffset:
        """
        EMA: offset_field = offset_field * (1 - SMOOTHING_FACTOR)
                             + delta_field * SMOOTHING_FACTOR

        Chỉ field nào có delta khác 0 mới bị đụng tới — field không nằm
        trong feedback lần này giữ nguyên offset cũ, không tự decay về 0.

        Clamp sau EMA theo khoảng offset hợp lệ suy ra từ
        QUIZ_PROFILE_BOUNDS - DEFAULT_QUIZ_PROFILE, để offset không bao
        giờ tự nó đẩy merged value ra ngoài [min, max] (miễn là
        DEFAULT_QUIZ_PROFILE không đổi giữa chừng).
        """
        offset = self.get_or_create_offset(user_id)

        for field in QUIZ_PROFILE_FIELDS:
            field_delta = delta.get(field, 0.0)
            if field_delta == 0:
                continue

            column_name = f"{field}_offset"
            current_offset = getattr(offset, column_name)
            new_offset = current_offset * (1 - SMOOTHING_FACTOR) + field_delta * SMOOTHING_FACTOR

            bounds = QUIZ_PROFILE_BOUNDS[field]
            default_value = DEFAULT_QUIZ_PROFILE[field]
            offset_min = bounds["min"] - default_value
            offset_max = bounds["max"] - default_value

            setattr(offset, column_name, _clamp(new_offset, offset_min, offset_max))

        self.db.commit()
        self.db.refresh(offset)

        return offset
