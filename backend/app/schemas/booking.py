from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator


class BookingCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_id: UUID
    provider_id: Optional[UUID] = None
    starts_at: AwareDatetime
    client_request_id: UUID
    customer_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    customer_email: EmailStr
    customer_phone: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]
    customer_notes: str = Field(default="", max_length=500)

    @field_validator("starts_at")
    @classmethod
    def starts_at_must_be_utc(cls, v: datetime) -> datetime:
        # Pydantic's AwareDatetime ensures it has tzinfo.
        # We'll normalize it to UTC just in case.
        from datetime import timezone

        return v.astimezone(timezone.utc)


class ServiceSnapshotPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    duration_minutes: int
    price_amount: int


class ProviderSnapshotPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str


class BookingPublicData(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    public_reference: str
    status: str
    service: ServiceSnapshotPublic
    provider: ProviderSnapshotPublic
    starts_at: datetime
    ends_at: datetime
    customer_email: str


class BookingPublicResponse(BaseModel):
    data: BookingPublicData
