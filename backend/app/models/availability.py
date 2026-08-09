import uuid

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKeyConstraint, Index, SmallInteger, String, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db import Base


class AvailabilityRule(Base):
    __tablename__ = "availability_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), nullable=False)
    provider_id = Column(UUID(as_uuid=True), nullable=False)
    weekday = Column(SmallInteger, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    provider = relationship("Provider", back_populates="availability_rules")

    __table_args__ = (
        ForeignKeyConstraint(
            ["business_id", "provider_id"], ["providers.business_id", "providers.id"], ondelete="CASCADE"
        ),  # noqa: E501
        CheckConstraint("weekday >= 0 AND weekday <= 6", name="check_weekday"),
        CheckConstraint("end_time > start_time", name="check_time_order"),
        Index("ix_avail_rules_b_p_w_s", "business_id", "provider_id", "weekday", "start_time"),
    )


class TimeOff(Base):
    __tablename__ = "time_off"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), nullable=False)
    provider_id = Column(UUID(as_uuid=True), nullable=False)
    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at = Column(DateTime(timezone=True), nullable=False)
    reason = Column(String(240), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    provider = relationship("Provider", back_populates="time_offs")

    __table_args__ = (
        ForeignKeyConstraint(
            ["business_id", "provider_id"], ["providers.business_id", "providers.id"], ondelete="CASCADE"
        ),  # noqa: E501
        CheckConstraint("ends_at > starts_at", name="check_time_off_order"),
        Index("ix_time_off_b_p_s", "business_id", "provider_id", "starts_at"),
    )
