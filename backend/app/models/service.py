import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db import Base


class Service(Base):
    __tablename__ = "services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=False, default="")
    duration_minutes = Column(Integer, nullable=False)
    price_amount = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    business = relationship("Business")
    providers = relationship(
        "ProviderService", back_populates="service", cascade="all, delete-orphan", overlaps="provider,provider_services"
    )  # noqa: E501

    __table_args__ = (
        CheckConstraint("duration_minutes >= 5 AND duration_minutes <= 720", name="check_duration"),
        CheckConstraint("price_amount >= 0", name="check_price"),
        UniqueConstraint("business_id", "id", name="uq_service_business"),
        Index("ix_services_business_active_sort", "business_id", "is_active", "sort_order"),
    )
