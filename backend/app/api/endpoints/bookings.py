from collections.abc import Callable

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.api.endpoints.availability import DomainError
from app.core.config import settings
from app.core.db import get_db
from app.core.dependencies import get_session_factory
from app.core.rate_limit import RateLimiter, RateLimitExceededError, get_subject_hash
from app.integrations.email.factory import get_email_service
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
    email_service = get_email_service(settings)
    return BookingService(db, availability_service, email_service)


router = APIRouter()


@router.post("/public/bookings", response_model=BookingPublicResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    request: BookingCreateRequest,
    response: Response,
    http_request: Request,
    db: Session = Depends(get_db),
    service: BookingService = Depends(get_booking_service),
    session_factory: Callable[[], Session] = Depends(get_session_factory),
):
    business_id = settings.BUSINESS_ID

    # 1. Check idempotency replay BEFORE rate limiting
    replay_status, existing_booking = service.check_idempotency_replay(
        business_id=business_id,
        client_request_id=request.client_request_id,
        request=request,
    )

    if replay_status == "VALID_REPLAY" and existing_booking is not None:
        response.status_code = status.HTTP_200_OK
        booking = existing_booking
    else:
        # 2. Rate limit consumption for incompatible replay or new request
        client_ip = http_request.client.host if http_request.client else None
        subject_hash = get_subject_hash(client_ip, settings.RATE_LIMIT_SECRET)
        limiter = RateLimiter(session_factory=session_factory, secret=settings.RATE_LIMIT_SECRET)
        is_allowed, _, retry_after = limiter.consume(
            endpoint="public_booking",
            subject_hash=subject_hash,
            limit=5,
            window_seconds=3600,
        )
        if not is_allowed:
            raise RateLimitExceededError(retry_after=retry_after)

        if replay_status == "INCOMPATIBLE_REPLAY":
            raise DomainError(
                code="idempotency_conflict",
                message="A different request with the same client_request_id already exists.",
                status_code=409,
            )

        # 3. Create public booking
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
