import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db import Base


class Provider(Base):
    __tablename__ = "providers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(120), nullable=False)
    email = Column(String(254), nullable=True)
    phone = Column(String(32), nullable=True)
    bio = Column(Text, nullable=False, default="")
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    business = relationship("Business")
    services = relationship(
        "ProviderService", back_populates="provider", cascade="all, delete-orphan", overlaps="providers"
    )  # noqa: E501
    availability_rules = relationship("AvailabilityRule", back_populates="provider", cascade="all, delete-orphan")
    time_offs = relationship("TimeOff", back_populates="provider", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("business_id", "id", name="uq_provider_business"),
        Index("ix_providers_business_active_sort", "business_id", "is_active", "sort_order"),
    )


class ProviderService(Base):
    __tablename__ = "provider_services"

    business_id = Column(UUID(as_uuid=True), nullable=False)
    provider_id = Column(UUID(as_uuid=True), nullable=False)
    service_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())

    provider = relationship("Provider", back_populates="services", overlaps="providers")
    service = relationship("Service", back_populates="providers", overlaps="provider,services")

    __table_args__ = (
        ForeignKeyConstraint(
            ["business_id", "provider_id"], ["providers.business_id", "providers.id"], ondelete="CASCADE"
        ),  # noqa: E501
        ForeignKeyConstraint(
            ["business_id", "service_id"], ["services.business_id", "services.id"], ondelete="CASCADE"
        ),  # noqa: E501
        PrimaryKeyConstraint("provider_id", "service_id", name="pk_provider_services"),
    )
