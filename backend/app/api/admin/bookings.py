from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.csrf import verify_origin
from app.core.db import get_db
from app.core.dependencies import get_current_admin, get_utc_now
from app.integrations.email.service import FakeEmailService, NoOpEmailService
from app.models.admin_user import AdminUser
from app.models.booking import BookingStatus
from app.schemas.admin import ResponseEnvelope
from app.schemas.booking_admin import (
    AdminBookingCreateRequest,
    AdminBookingDetail,
    AdminBookingListItem,
    AdminBookingStatusUpdate,
)
from app.services.availability_service import AvailabilityService
from app.services.booking_service import BookingService

router = APIRouter(prefix="/bookings", tags=["Admin Bookings"])


def get_booking_service(db: Annotated[Session, Depends(get_db)]) -> BookingService:
    availability_service = AvailabilityService(db)
    email_service = FakeEmailService()
    return BookingService(db, availability_service, email_service)


def get_booking_service_admin(db: Annotated[Session, Depends(get_db)]) -> BookingService:
    availability_service = AvailabilityService(db)
    email_service = NoOpEmailService()
    return BookingService(db, availability_service, email_service)


@router.post("", response_model=ResponseEnvelope[AdminBookingDetail], status_code=status.HTTP_201_CREATED)
def create_admin_booking(
    request: AdminBookingCreateRequest,
    current_admin: Annotated[AdminUser, Depends(get_current_admin)],
    service: Annotated[BookingService, Depends(get_booking_service_admin)],
    response: Response,
    _: Annotated[None, Depends(verify_origin)],
) -> ResponseEnvelope[AdminBookingDetail]:
    booking, created = service.create_admin_booking(business_id=current_admin.business_id, request=request)
    if not created:
        response.status_code = status.HTTP_200_OK

    detail = service.get_admin_booking_detail(business_id=current_admin.business_id, booking_id=booking.id)
    return ResponseEnvelope(data=detail)


@router.get("", response_model=ResponseEnvelope[list[AdminBookingListItem]])
def list_admin_bookings(
    current_admin: Annotated[AdminUser, Depends(get_current_admin)],
    service: Annotated[BookingService, Depends(get_booking_service)],
    now: Annotated[datetime, Depends(get_utc_now)],
    date: Annotated[date | None, Query()] = None,
    status: Annotated[BookingStatus | None, Query()] = None,
    provider_id: Annotated[UUID | None, Query()] = None,
) -> ResponseEnvelope[list[AdminBookingListItem]]:
    items = service.get_admin_bookings(
        business_id=current_admin.business_id,
        target_date=date,
        status_filter=status,
        provider_id=provider_id,
        now=now,
    )
    return ResponseEnvelope(data=items)


@router.get("/{booking_id}", response_model=ResponseEnvelope[AdminBookingDetail])
def get_admin_booking_detail(
    booking_id: UUID,
    current_admin: Annotated[AdminUser, Depends(get_current_admin)],
    service: Annotated[BookingService, Depends(get_booking_service)],
) -> ResponseEnvelope[AdminBookingDetail]:
    detail = service.get_admin_booking_detail(
        business_id=current_admin.business_id,
        booking_id=booking_id,
    )
    return ResponseEnvelope(data=detail)


@router.patch(
    "/{booking_id}/status",
    response_model=ResponseEnvelope[AdminBookingDetail],
    dependencies=[Depends(verify_origin)],
)
def update_admin_booking_status(
    booking_id: UUID,
    payload: AdminBookingStatusUpdate,
    current_admin: Annotated[AdminUser, Depends(get_current_admin)],
    service: Annotated[BookingService, Depends(get_booking_service)],
    now: Annotated[datetime, Depends(get_utc_now)],
) -> ResponseEnvelope[AdminBookingDetail]:
    detail = service.update_booking_status(
        business_id=current_admin.business_id,
        booking_id=booking_id,
        new_status=payload.status,
        now=now,
    )
    return ResponseEnvelope(data=detail)
