from sqlalchemy import Column, DateTime, Index, Integer, PrimaryKeyConstraint, String

from app.core.db import Base


class RateLimit(Base):
    __tablename__ = "rate_limits"

    subject_hash = Column(String(64), nullable=False)
    endpoint = Column(String(50), nullable=False)
    window_start = Column(DateTime(timezone=True), nullable=False)
    count = Column(Integer, nullable=False, default=1)

    __table_args__ = (
        PrimaryKeyConstraint("subject_hash", "endpoint", "window_start", name="pk_rate_limits"),
        Index("idx_rate_limits_window", "window_start"),
    )
