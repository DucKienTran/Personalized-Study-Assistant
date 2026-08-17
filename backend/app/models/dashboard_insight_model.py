from sqlalchemy import JSON, Column, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.mysql import BIGINT

from app.core.database import Base


class DashboardInsightCache(Base):
    __tablename__ = "dashboard_insight_caches"

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    user_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    insight_text = Column(Text, nullable=False)
    selected_stats = Column(JSON, nullable=False)
    source_attempt_id = Column(BIGINT(unsigned=True), nullable=True)
    source_attempt_updated_at = Column(DateTime(timezone=True), nullable=True)
    generated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
