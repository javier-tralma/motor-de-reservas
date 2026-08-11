from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.booking import BookingSource, BookingStatus


class AdminBookingStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: BookingStatus

    @field_validator("status")
    @classmethod
    def validate_allowed_status(cls, v: BookingStatus) -> BookingStatus:
        allowed = {BookingStatus.completed, BookingStatus.cancelled, BookingStatus.no_show}
        if v not in allowed:
            raise ValueError(f"Estado no permitido para actualización: {v}")
        return v


class AdminBookingListItem(BaseModel):
    id: UUID
    starts_at: datetime
    ends_at: datetime
    customer_name: str
    service_name_snapshot: str
    provider_name_snapshot: str
    provider_id: UUID
    status: BookingStatus
    source: BookingSource


class AdminBookingDetail(BaseModel):
    id: UUID
    public_reference: str
    customer_name: str
    customer_email: str
    customer_phone: str
    customer_notes: str
    starts_at: datetime
    ends_at: datetime
    status: BookingStatus
    source: BookingSource
    service_id: UUID
    provider_id: UUID
    service_name_snapshot: str
    provider_name_snapshot: str
    duration_minutes_snapshot: int
    price_amount_snapshot: int
    cancelled_at: datetime | None = None
    completed_at: datetime | None = None
    no_show_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AdminProviderListItem(BaseModel):
    id: UUID
    name: str
    is_active: bool
