import uuid

from sqlalchemy import CheckConstraint, Column, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.core.db import Base


class Business(Base):
    __tablename__ = "businesses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(120), nullable=False)
    slug = Column(String(80), nullable=False, unique=True)
    timezone = Column(String(64), nullable=False, default="America/Santiago")
    locale = Column(String(16), nullable=False, default="es-CL")
    currency = Column(String(3), nullable=False, default="CLP")
    email = Column(String(254), nullable=False)
    phone = Column(String(32), nullable=True)
    address = Column(String(300), nullable=True)
    minimum_booking_notice_minutes = Column(Integer, nullable=False, default=120)
    booking_horizon_days = Column(Integer, nullable=False, default=60)
    slot_interval_minutes = Column(Integer, nullable=False, default=15)

    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("minimum_booking_notice_minutes >= 0", name="check_min_notice"),
        CheckConstraint("booking_horizon_days >= 1 AND booking_horizon_days <= 365", name="check_horizon"),
        CheckConstraint("slot_interval_minutes >= 1 AND slot_interval_minutes <= 120", name="check_slot_interval"),
    )
