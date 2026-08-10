import uuid
from datetime import timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.endpoints.availability import DomainError
from app.core.config import settings
from app.core.db import get_db
from app.models.booking import Booking
from app.models.business import Business
from app.models.provider import Provider, ProviderService
from app.models.service import Service
from app.schemas.public import (
    BookingConfirmationPublicData,
    BookingConfirmationPublicResponse,
    BusinessContactPublic,
    BusinessPublicData,
    BusinessPublicResponse,
    ProviderListPublicResponse,
    ProviderPublicData,
    ProviderSnapshotPublic,
    ServiceListPublicResponse,
    ServicePublicData,
    ServiceSnapshotPublic,
)

router = APIRouter()


def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return email
    parts = email.split("@", 1)
    name, domain = parts[0], parts[1]
    if len(name) <= 2:
        masked_name = name[0] + "*" if name else "*"
    else:
        masked_name = name[0] + "*" * (len(name) - 2) + name[-1]
    return f"{masked_name}@{domain}"


@router.get("/public/business", response_model=BusinessPublicResponse)
def get_public_business(db: Session = Depends(get_db)):
    business = db.execute(select(Business).filter_by(id=settings.BUSINESS_ID)).scalar_one_or_none()

    if not business:
        raise DomainError(code="business_not_found", message="Business not found", status_code=404)

    return BusinessPublicResponse(
        data=BusinessPublicData(
            name=business.name,
            slug=business.slug,
            timezone=business.timezone,
            locale=business.locale,
            currency=business.currency,
            email=business.email,
            phone=business.phone,
            address=business.address,
            booking_horizon_days=business.booking_horizon_days,
        )
    )


@router.get("/public/services", response_model=ServiceListPublicResponse)
def get_public_services(db: Session = Depends(get_db)):
    services = (
        db.execute(
            select(Service)
            .filter_by(business_id=settings.BUSINESS_ID, is_active=True)
            .order_by(Service.sort_order.asc(), Service.name.asc())
        )
        .scalars()
        .all()
    )

    data = [
        ServicePublicData(
            id=s.id,
            name=s.name,
            description=s.description,
            duration_minutes=s.duration_minutes,
            price_amount=s.price_amount,
        )
        for s in services
    ]

    return ServiceListPublicResponse(data=data)


@router.get("/public/services/{service_id}/providers", response_model=ProviderListPublicResponse)
def get_public_service_providers(service_id: uuid.UUID, db: Session = Depends(get_db)):
    # 1. Verificar que el servicio existe, pertenece al negocio y está activo
    service = db.execute(
        select(Service).filter_by(id=service_id, business_id=settings.BUSINESS_ID, is_active=True)
    ).scalar_one_or_none()

    if not service:
        raise DomainError(code="service_unavailable", message="Service is not available", status_code=404)

    # 2. Buscar profesionales activos asociados al servicio y pertenecientes al negocio
    providers = (
        db.execute(
            select(Provider)
            .join(ProviderService, Provider.id == ProviderService.provider_id)
            .filter(
                ProviderService.service_id == service_id,
                ProviderService.business_id == settings.BUSINESS_ID,
                Provider.business_id == settings.BUSINESS_ID,
                Provider.is_active == True,  # noqa: E712
            )
            .order_by(Provider.sort_order.asc(), Provider.name.asc())
        )
        .scalars()
        .all()
    )

    data = [
        ProviderPublicData(
            id=p.id,
            name=p.name,
            bio=p.bio,
        )
        for p in providers
    ]

    return ProviderListPublicResponse(data=data)


@router.get("/public/bookings/{public_reference}/confirmation", response_model=BookingConfirmationPublicResponse)
def get_booking_confirmation(public_reference: str, db: Session = Depends(get_db)):
    # 1. Buscar conjuntamente por business_id y public_reference
    booking = db.execute(
        select(Booking).filter_by(business_id=settings.BUSINESS_ID, public_reference=public_reference)
    ).scalar_one_or_none()

    if not booking:
        raise DomainError(code="booking_not_found", message="Booking not found", status_code=404)

    # 2. Cargar datos de contacto del negocio
    business = db.execute(select(Business).filter_by(id=settings.BUSINESS_ID)).scalar_one_or_none()

    business_contact = BusinessContactPublic(
        name=business.name if business else "Estudio Nómada",
        email=business.email if business else "",
        phone=business.phone if business else None,
        address=business.address if business else None,
        timezone=business.timezone if business else "America/Santiago",
    )

    tz_name = business.timezone if business and business.timezone else "America/Santiago"
    biz_tz = ZoneInfo(tz_name)

    starts_utc = booking.starts_at if booking.starts_at.tzinfo else booking.starts_at.replace(tzinfo=timezone.utc)
    ends_utc = booking.ends_at if booking.ends_at.tzinfo else booking.ends_at.replace(tzinfo=timezone.utc)

    data = BookingConfirmationPublicData(
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
        starts_at=starts_utc.astimezone(biz_tz),
        ends_at=ends_utc.astimezone(biz_tz),
        customer_email_masked=mask_email(booking.customer_email),
        business=business_contact,
    )

    return BookingConfirmationPublicResponse(data=data)
