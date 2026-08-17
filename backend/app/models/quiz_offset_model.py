from sqlalchemy import Column, DateTime, Float, ForeignKey, func
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserQuizProfileOffset(Base):
    """
    Lưu personal offset của từng user, cộng vào DEFAULT_QUIZ_PROFILE
    (app/core/constants/quiz_profile.py) để ra merged profile cuối
    cùng dùng khi generate quiz.

    Chỉ lưu OFFSET, không lưu merged profile — merge diễn ra lúc đọc
    (personal_offset_service.get_merged_profile), nên đổi
    DEFAULT_QUIZ_PROFILE không cần touch bảng này.

    Mỗi cột ứng với đúng 1 field trong QUIZ_PROFILE_FIELDS. Thêm/bớt
    field ở quiz_profile.py thì phải thêm/bớt cột + migration tương ứng
    ở đây (2 chỗ này luôn phải đồng bộ).
    """

    __tablename__ = "quiz_profile_offsets"

    id = Column(BIGINT(unsigned=True), primary_key=True, index=True, autoincrement=True)

    user_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # mỗi user chỉ có đúng 1 dòng offset (global, chưa theo notebook)
    )

    difficulty_offset = Column(Float, nullable=False, default=0.0, server_default="0.0")
    coverage_offset = Column(Float, nullable=False, default=0.0, server_default="0.0")
    reasoning_depth_offset = Column(Float, nullable=False, default=0.0, server_default="0.0")
    anti_repetition_offset = Column(Float, nullable=False, default=0.0, server_default="0.0")
    relevance_offset = Column(Float, nullable=False, default=0.0, server_default="0.0")
    time_per_question_offset = Column(Float, nullable=False, default=0.0, server_default="0.0")
    strict_source_grounding_offset = Column(Float, nullable=False, default=0.0, server_default="0.0")

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship("User")
