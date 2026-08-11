from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., max_length=254)
    password: str = Field(..., min_length=1, max_length=128)


class AdminInfo(BaseModel):
    id: UUID
    display_name: str
    email: str


class BusinessInfo(BaseModel):
    name: str
    timezone: str
    locale: str


class AuthResponseData(BaseModel):
    admin: AdminInfo
    business: BusinessInfo


class AuthResponse(BaseModel):
    data: AuthResponseData


class DashboardSummary(BaseModel):
    total: int
    confirmed_remaining: int
    completed: int
    cancelled: int
    no_show: int


class BookingAgendaItem(BaseModel):
    id: UUID
    starts_at: str
    ends_at: str
    customer_name: str
    service_name: str
    provider_name: str
    status: str


class DashboardData(BaseModel):
    date: str
    timezone: str
    summary: DashboardSummary
    next_booking: BookingAgendaItem | None
    agenda: list[BookingAgendaItem]


class DashboardResponse(BaseModel):
    data: DashboardData
