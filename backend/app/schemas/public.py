from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class BusinessPublicData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    slug: str
    timezone: str
    locale: str
    currency: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    booking_horizon_days: int


class BusinessPublicResponse(BaseModel):
    data: BusinessPublicData


class ServicePublicData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str
    duration_minutes: int
    price_amount: int


class ServiceListPublicResponse(BaseModel):
    data: List[ServicePublicData]


class ProviderPublicData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    bio: str


class ProviderListPublicResponse(BaseModel):
    data: List[ProviderPublicData]


class BusinessContactPublic(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    timezone: str = "America/Santiago"


class ServiceSnapshotPublic(BaseModel):
    name: str
    duration_minutes: int
    price_amount: int


class ProviderSnapshotPublic(BaseModel):
    name: str


class BookingConfirmationPublicData(BaseModel):
    public_reference: str
    status: str
    service: ServiceSnapshotPublic
    provider: ProviderSnapshotPublic
    starts_at: datetime
    ends_at: datetime
    customer_email_masked: str
    business: BusinessContactPublic


class BookingConfirmationPublicResponse(BaseModel):
    data: BookingConfirmationPublicData
