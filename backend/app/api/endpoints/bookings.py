from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.integrations.email.service import ConsoleEmailService
from app.schemas.booking import (
    BookingCreateRequest,
    BookingPublicData,
    BookingPublicResponse,
    ProviderSnapshotPublic,
    ServiceSnapshotPublic,
)
from app.services.availability_service import AvailabilityService
from app.services.booking_service import BookingService


def get_booking_service(db: Session = Depends(get_db)) -> BookingService:
    availability_service = AvailabilityService(db)
    # Use ConsoleEmailService for development as requested
    email_service = ConsoleEmailService()
    return BookingService(db, availability_service, email_service)


router = APIRouter()


@router.post("/public/bookings", response_model=BookingPublicResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    request: BookingCreateRequest,
    response: Response,
    service: BookingService = Depends(get_booking_service),
):

    # 1. Resolver el negocio (por configuración/ambiente, P0 usa settings.BUSINESS_ID)
    business_id = settings.BUSINESS_ID

    # El BookingService verificará y lanzará excepción si no coincide el hash.
    # Para enviar status_code dinámico (200 OK vs 201 Created),
    # podríamos devolver un flag o chequear DB antes.
    # Aquí chequeamos de forma efímera.

    booking, created = service.create_public_booking(business_id, request)

    if not created:
        response.status_code = status.HTTP_200_OK

    public_data = BookingPublicData(
        public_reference=booking.public_reference,
        status=booking.status.value,
        service=ServiceSnapshotPublic(
            name=booking.service_name_snapshot,
            duration_minutes=booking.duration_minutes_snapshot,
            price_amount=booking.price_amount_snapshot,
        ),
        provider=ProviderSnapshotPublic(
            name=booking.provider_name_snapshot,
        ),
        starts_at=booking.starts_at,
        ends_at=booking.ends_at,
        customer_email=booking.customer_email,
    )

    return BookingPublicResponse(data=public_data)
