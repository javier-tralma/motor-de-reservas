import enum
import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, UUID, ExcludeConstraint
from sqlalchemy.sql import func

from app.core.db import Base


class BookingStatus(str, enum.Enum):
    confirmed = "confirmed"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"


class BookingSource(str, enum.Enum):
    public = "public"
    admin = "admin"


class EmailDeliveryStatus(str, enum.Enum):
    not_requested = "not_requested"
    pending = "pending"
    sent = "sent"
    failed = "failed"


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), nullable=False)
    service_id = Column(UUID(as_uuid=True), nullable=False)
    provider_id = Column(UUID(as_uuid=True), nullable=False)

    public_reference = Column(String(64), nullable=False, unique=True)
    client_request_id = Column(UUID(as_uuid=True), nullable=True)
    request_fingerprint = Column(String(64), nullable=True)

    customer_name = Column(String(120), nullable=False)
    customer_email = Column(String(254), nullable=False)
    customer_phone = Column(String(32), nullable=False)
    customer_notes = Column(Text, nullable=False, default="")

    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at = Column(DateTime(timezone=True), nullable=False)

    status = Column(
        ENUM(BookingStatus, name="booking_status", create_type=False), nullable=False, default=BookingStatus.confirmed
    )  # noqa: E501
    source = Column(ENUM(BookingSource, name="booking_source", create_type=False), nullable=False)

    service_name_snapshot = Column(String(120), nullable=False)
    duration_minutes_snapshot = Column(Integer, nullable=False)
    price_amount_snapshot = Column(Integer, nullable=False)
    provider_name_snapshot = Column(String(120), nullable=False)

    email_delivery_status = Column(
        ENUM(EmailDeliveryStatus, name="email_delivery_status", create_type=False), nullable=False
    )  # noqa: E501
    email_provider_id = Column(String(160), nullable=True)
    email_sent_at = Column(DateTime(timezone=True), nullable=True)
    email_last_error_code = Column(String(80), nullable=True)

    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    __table_args__ = (
        ForeignKeyConstraint(
            ["business_id", "provider_id"], ["providers.business_id", "providers.id"], ondelete="RESTRICT"
        ),  # noqa: E501
        ForeignKeyConstraint(
            ["business_id", "service_id"], ["services.business_id", "services.id"], ondelete="RESTRICT"
        ),  # noqa: E501
        UniqueConstraint("business_id", "client_request_id", name="uq_business_client_request"),
        Index("ix_bookings_business_starts", "business_id", "starts_at"),
        Index("ix_bookings_business_provider_starts", "business_id", "provider_id", "starts_at"),
        Index("ix_bookings_business_status_starts", "business_id", "status", "starts_at"),
        CheckConstraint("ends_at > starts_at", name="check_booking_ends_at"),
        CheckConstraint("duration_minutes_snapshot > 0", name="check_booking_duration"),
        CheckConstraint("price_amount_snapshot >= 0", name="check_booking_price"),
        ExcludeConstraint(
            ("provider_id", "="),
            (func.tstzrange(starts_at, ends_at, "[)"), "&&"),
            where=text("status != 'cancelled'"),
            name="bookings_provider_no_overlap",
            using="gist",  # noqa: E501
        ),
    )
