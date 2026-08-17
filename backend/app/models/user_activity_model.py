from sqlalchemy import DATE, TIMESTAMP, Column, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class UserDailyActivity(Base):
    __tablename__ = "user_daily_activities"
    __table_args__ = (
        UniqueConstraint("user_id", "activity_date", name="uq_user_daily_activity_date"),
    )

    id = Column(BIGINT(unsigned=True), primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activity_date = Column(DATE, nullable=False, index=True)
    active_seconds = Column(Integer, nullable=False, default=0)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User")
