import hashlib
import json
import secrets
import string
import uuid
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import psycopg
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.endpoints.availability import DomainError
from app.integrations.email.service import BookingEmailData, EmailDeliveryStatus, EmailResult, EmailService
from app.models.booking import Booking, BookingSource, BookingStatus
from app.models.business import Business
from app.models.provider import Provider
from app.models.service import Service
from app.schemas.booking import BookingCreateRequest
from app.schemas.booking_admin import (
    AdminBookingCreateRequest,
    AdminBookingDetail,
    AdminBookingListItem,
    AdminProviderListItem,
)
from app.services.availability_service import AvailabilityService


class BookingService:
    def __init__(self, db: Session, availability_service: AvailabilityService, email_service: EmailService):
        self.db = db
        self.availability_service = availability_service
        self.email_service = email_service

    def _create_booking_core(
        self,
        business_id: uuid.UUID,
        request: BookingCreateRequest | AdminBookingCreateRequest,
        source: BookingSource,
        initial_email_status: EmailDeliveryStatus,
    ) -> tuple[Booking, bool, BookingEmailData | None, Business]:
        # 1. Resolver el negocio para la zona horaria y validaciones
        business = self.db.execute(select(Business).filter_by(id=business_id)).scalar_one_or_none()
        if not business:
            raise DomainError(code="business_not_found", message="Business not found", status_code=404)

        # 2. Generar el fingerprint de la petición para idempotencia
        fingerprint = self._generate_fingerprint(request)

        # 3. Validar idempotencia normal consultando si ya existe (para requests secuenciales)
        replay = self._check_idempotency_fallback(business_id, request.client_request_id, fingerprint, expire_all=False)
        if replay:
            return replay[0], replay[1], None, business

        # 4. Validar que el servicio exista y esté activo
        service = self.db.execute(
            select(Service).filter_by(id=request.service_id, business_id=business_id, is_active=True)
        ).scalar_one_or_none()
        if not service:
            raise DomainError(code="service_unavailable", message="Service is not available", status_code=404)

        # 5. Obtener los candidatos (profesionales) usando AvailabilityService
        # Necesitamos saber la fecha civil local (en el timezone del negocio)
        local_tz = ZoneInfo(business.timezone)
        starts_at_local = request.starts_at.astimezone(local_tz)
        target_date = starts_at_local.date()

        availability_result = self.availability_service.get_availability(
            business_id=business_id,
            service_id=request.service_id,
            target_date=target_date,
            provider_id=request.provider_id,
        )

        # Buscar el slot específico
        valid_slots = [s for s in availability_result["slots"] if s.starts_at.astimezone(local_tz) == starts_at_local]

        if not valid_slots:
            replay = self._check_idempotency_fallback(business_id, request.client_request_id, fingerprint)
            if replay:
                return replay[0], replay[1], None, business
            raise DomainError(code="slot_unavailable", message="The requested slot is not available.", status_code=409)

        # 6. Intentar reservar con los candidatos disponibles (de forma determinista)
        # AvailabilityEngine ya devuelve ordenado por starts_at y provider_id (que es UUID, así que es estable)
        candidate_providers = [slot.provider_id for slot in valid_slots]
        ends_at_utc = valid_slots[0].ends_at  # Todos tienen la misma duración

        # 7. Proceder a la inserción con transacciones anidadas (savepoints)
        for provider_id in candidate_providers:
            # Lock the provider to serialize concurrent insertions and prevent GiST deadlocks
            provider = self.db.execute(
                select(Provider).filter_by(id=provider_id, business_id=business_id).with_for_update()
            ).scalar_one()

            # Preparamos el modelo
            public_reference = self._generate_public_reference()

            new_booking = Booking(
                business_id=business_id,
                service_id=service.id,
                provider_id=provider.id,
                public_reference=public_reference,
                client_request_id=request.client_request_id,
                request_fingerprint=fingerprint,
                customer_name=request.customer_name,
                customer_email=request.customer_email,
                customer_phone=request.customer_phone,
                customer_notes=request.customer_notes,
                starts_at=request.starts_at,
                ends_at=ends_at_utc,
                status=BookingStatus.confirmed,
                source=source,
                service_name_snapshot=service.name,
                duration_minutes_snapshot=service.duration_minutes,
                price_amount_snapshot=service.price_amount,
                provider_name_snapshot=provider.name,
                email_delivery_status=initial_email_status,
            )

            try:
                # Savepoint para intentar este provider
                with self.db.begin_nested():
                    self.db.add(new_booking)
            except IntegrityError as e:
                # Verificamos si es una violación de exclusión de PostgreSQL (solapamiento concurrente)
                if (
                    isinstance(e.orig, psycopg.errors.ExclusionViolation)
                    and e.orig.diag.constraint_name == "bookings_provider_no_overlap"
                ):
                    # El constraint `bookings_provider_no_overlap` saltó.
                    # Este provider ya no está disponible, probamos con el siguiente.
                    continue
                elif (
                    isinstance(e.orig, psycopg.errors.UniqueViolation)
                    and e.orig.diag.constraint_name == "uq_business_client_request"
                ):
                    # Replay (idempotencia concurrente)
                    # Ocurrió una carrera y el otro thread ganó
                    existing_booking = self.db.execute(
                        select(Booking).filter_by(business_id=business_id, client_request_id=request.client_request_id)
                    ).scalar_one()

                    if existing_booking.request_fingerprint == fingerprint:
                        return existing_booking, False, None, business
                    else:
                        raise DomainError(
                            code="idempotency_conflict",
                            message="A different request with the same client_request_id already exists.",
                            status_code=409,
                        )
                else:
                    # Otra integridad (ej. public_reference), re-lanzamos
                    raise DomainError(
                        code="database_error", message="Unexpected integrity error", status_code=500
                    ) from e

            email_data = None
            if initial_email_status != EmailDeliveryStatus.not_requested:
                email_data = BookingEmailData(
                    booking_id=new_booking.id,
                    public_reference=new_booking.public_reference,
                    customer_name=new_booking.customer_name,
                    customer_email=new_booking.customer_email,
                    starts_at=new_booking.starts_at,
                    ends_at=new_booking.ends_at,
                    duration_minutes=new_booking.duration_minutes_snapshot,
                    service_name=new_booking.service_name_snapshot,
                    provider_name=new_booking.provider_name_snapshot,
                    business_name=business.name,
                    business_timezone=business.timezone,
                    business_address=business.address,
                    business_phone=business.phone,
                )

            return new_booking, True, email_data, business

        # Si agotamos todos los candidatos sin éxito, el slot realmente no está disponible
        replay = self._check_idempotency_fallback(business_id, request.client_request_id, fingerprint)
        if replay:
            return replay[0], replay[1], None, business

        raise DomainError(code="slot_unavailable", message="The requested slot is not available.", status_code=409)

    def create_public_booking(self, business_id: uuid.UUID, request: BookingCreateRequest) -> tuple[Booking, bool]:
        booking, created, email_data, business = self._create_booking_core(
            business_id,
            request,
            source=BookingSource.public,
            initial_email_status=EmailDeliveryStatus.pending,
        )

        if created and email_data:
            self.db.commit()
            self._send_confirmation_email(
                email_data=email_data,
                business_id=business_id,
            )

        return booking, created

    def create_admin_booking(self, business_id: uuid.UUID, request: AdminBookingCreateRequest) -> tuple[Booking, bool]:
        booking, created, email_data, business = self._create_booking_core(
            business_id,
            request,
            source=BookingSource.admin,
            initial_email_status=EmailDeliveryStatus.not_requested,
        )

        if created:
            self.db.commit()

        return booking, created

    def _generate_fingerprint(self, request: BookingCreateRequest | AdminBookingCreateRequest) -> str:
        # Canonical string for idempotency matching
        from datetime import timezone

        canonical_dict = {
            "service_id": str(request.service_id),
            "provider_id": str(request.provider_id) if request.provider_id else None,
            "starts_at": request.starts_at.astimezone(timezone.utc).isoformat(),
            "customer_name": request.customer_name,
            "customer_email": request.customer_email.lower(),
            "customer_phone": request.customer_phone,
            "customer_notes": request.customer_notes,
        }
        canonical_str = json.dumps(canonical_dict, sort_keys=True)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def check_idempotency_replay(
        self,
        business_id: uuid.UUID,
        client_request_id: uuid.UUID | None,
        request: BookingCreateRequest,
    ) -> tuple[str, Booking | None]:
        """
        Explicit, read-only check to resolve idempotency before rate limiting or domain execution.
        Returns:
            ("VALID_REPLAY", existing_booking) if valid replay (same fingerprint).
            ("INCOMPATIBLE_REPLAY", None) if existing booking has a different fingerprint.
            ("NEW", None) if client_request_id is None or no existing booking exists.
        """
        if not client_request_id:
            return ("NEW", None)

        fingerprint = self._generate_fingerprint(request)
        existing_booking = self.db.execute(
            select(Booking).filter_by(business_id=business_id, client_request_id=client_request_id)
        ).scalar_one_or_none()

        if existing_booking:
            if existing_booking.request_fingerprint == fingerprint:
                return ("VALID_REPLAY", existing_booking)
            else:
                return ("INCOMPATIBLE_REPLAY", None)

        return ("NEW", None)

    def _check_idempotency_fallback(
        self, business_id: uuid.UUID, client_request_id: uuid.UUID | None, fingerprint: str, expire_all: bool = True
    ) -> tuple[Booking, bool] | None:

        if not client_request_id:
            return None

        if expire_all:
            self.db.expire_all()

        existing_booking = self.db.execute(
            select(Booking).filter_by(business_id=business_id, client_request_id=client_request_id)
        ).scalar_one_or_none()

        if existing_booking:
            if existing_booking.request_fingerprint == fingerprint:
                return existing_booking, False
            else:
                raise DomainError(
                    code="idempotency_conflict",
                    message="A different request with the same client_request_id already exists.",
                    status_code=409,
                )
        return None

    def _generate_public_reference(self) -> str:
        # Generar una referencia URL-safe, aleatoria, no secuencial.
        characters = string.ascii_letters + string.digits
        return "".join(secrets.choice(characters) for _ in range(12))

    def _send_confirmation_email(self, email_data: BookingEmailData, business_id: uuid.UUID):
        assert self.db.in_transaction() is False, "Email service called within an active transaction"

        try:
            email_result = self.email_service.send_booking_confirmation(email_data)
        except Exception:
            email_result = EmailResult(status=EmailDeliveryStatus.failed, error_code="provider_exception")

        # Actualizamos el estado del email en una nueva transacción corta
        try:
            booking_update = self.db.execute(
                select(Booking).filter_by(id=email_data.booking_id, business_id=business_id)
            ).scalar_one()
            booking_update.email_delivery_status = email_result.status
            booking_update.email_provider_id = email_result.provider_id
            booking_update.email_last_error_code = email_result.error_code

            if email_result.status == EmailDeliveryStatus.sent:
                booking_update.email_sent_at = datetime.now(timezone.utc)

            self.db.commit()
        except Exception:
            self.db.rollback()

    def get_admin_bookings(
        self,
        business_id: uuid.UUID,
        target_date: date | None,
        status_filter: BookingStatus | None,
        provider_id: uuid.UUID | None,
        now: datetime,
    ) -> list[AdminBookingListItem]:
        business = self.db.execute(select(Business).filter_by(id=business_id)).scalar_one_or_none()
        if not business:
            raise DomainError(code="business_not_found", message="Business not found", status_code=404)

        if provider_id:
            provider = self.db.execute(
                select(Provider).filter_by(id=provider_id, business_id=business_id)
            ).scalar_one_or_none()
            if not provider:
                return []

        local_tz = ZoneInfo(business.timezone)
        if target_date is None:
            now_utc = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
            now_local = now_utc.astimezone(local_tz)
            target_date = now_local.date()

        from app.domain.time_utils import get_local_day_bounds_utc

        start_utc, end_utc = get_local_day_bounds_utc(target_date, business.timezone)

        query = select(Booking).filter(
            Booking.business_id == business_id,
            Booking.starts_at >= start_utc,
            Booking.starts_at < end_utc,
        )
        if status_filter:
            query = query.filter(Booking.status == status_filter)
        if provider_id:
            query = query.filter(Booking.provider_id == provider_id)

        query = query.order_by(Booking.starts_at.asc())
        bookings = self.db.execute(query).scalars().all()

        items = []
        for b in bookings:
            starts_utc = b.starts_at if b.starts_at.tzinfo else b.starts_at.replace(tzinfo=timezone.utc)
            ends_utc = b.ends_at if b.ends_at.tzinfo else b.ends_at.replace(tzinfo=timezone.utc)
            items.append(
                AdminBookingListItem(
                    id=b.id,
                    starts_at=starts_utc.astimezone(local_tz),
                    ends_at=ends_utc.astimezone(local_tz),
                    customer_name=b.customer_name,
                    service_name_snapshot=b.service_name_snapshot,
                    provider_name_snapshot=b.provider_name_snapshot,
                    provider_id=b.provider_id,
                    status=b.status,
                    source=b.source,
                )
            )
        return items

    def get_admin_booking_detail(
        self,
        business_id: uuid.UUID,
        booking_id: uuid.UUID,
    ) -> AdminBookingDetail:
        business = self.db.execute(select(Business).filter_by(id=business_id)).scalar_one_or_none()
        if not business:
            raise DomainError(code="business_not_found", message="Business not found", status_code=404)

        booking = self.db.execute(
            select(Booking).filter_by(id=booking_id, business_id=business_id)
        ).scalar_one_or_none()

        if not booking:
            raise DomainError(code="booking_not_found", message="Booking not found", status_code=404)

        local_tz = ZoneInfo(business.timezone)

        def to_local(dt: datetime | None) -> datetime | None:
            if dt is None:
                return None
            dt_utc = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            return dt_utc.astimezone(local_tz)

        return AdminBookingDetail(
            id=booking.id,
            public_reference=booking.public_reference,
            customer_name=booking.customer_name,
            customer_email=booking.customer_email,
            customer_phone=booking.customer_phone,
            customer_notes=booking.customer_notes,
            starts_at=to_local(booking.starts_at),
            ends_at=to_local(booking.ends_at),
            status=booking.status,
            source=booking.source,
            service_id=booking.service_id,
            provider_id=booking.provider_id,
            service_name_snapshot=booking.service_name_snapshot,
            provider_name_snapshot=booking.provider_name_snapshot,
            duration_minutes_snapshot=booking.duration_minutes_snapshot,
            price_amount_snapshot=booking.price_amount_snapshot,
            cancelled_at=to_local(booking.cancelled_at),
            completed_at=to_local(booking.completed_at),
            no_show_at=to_local(booking.no_show_at),
            created_at=to_local(booking.created_at),
            updated_at=to_local(booking.updated_at),
        )

    def update_booking_status(
        self,
        business_id: uuid.UUID,
        booking_id: uuid.UUID,
        new_status: BookingStatus,
        now: datetime,
    ) -> AdminBookingDetail:
        business = self.db.execute(select(Business).filter_by(id=business_id)).scalar_one_or_none()
        if not business:
            raise DomainError(code="business_not_found", message="Business not found", status_code=404)

        try:
            booking = self.db.execute(
                select(Booking).filter_by(id=booking_id, business_id=business_id).with_for_update()
            ).scalar_one_or_none()

            if not booking:
                raise DomainError(code="booking_not_found", message="Booking not found", status_code=404)

            if booking.status != BookingStatus.confirmed:
                raise DomainError(
                    code="invalid_status_transition",
                    message=f"Cannot transition booking from {booking.status} to {new_status}",
                    status_code=409,
                )

            now_utc = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
            booking.status = new_status
            if new_status == BookingStatus.cancelled:
                booking.cancelled_at = now_utc
            elif new_status == BookingStatus.completed:
                booking.completed_at = now_utc
            elif new_status == BookingStatus.no_show:
                booking.no_show_at = now_utc

            self.db.commit()
            self.db.refresh(booking)
        except DomainError:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            raise DomainError(code="database_error", message="Failed to update booking status", status_code=500) from e

        return self.get_admin_booking_detail(business_id=business_id, booking_id=booking_id)

    def get_admin_providers(self, business_id: uuid.UUID) -> list[AdminProviderListItem]:
        providers = (
            self.db.execute(
                select(Provider)
                .filter_by(business_id=business_id)
                .order_by(Provider.sort_order.asc(), Provider.name.asc())
            )
            .scalars()
            .all()
        )

        return [AdminProviderListItem(id=p.id, name=p.name, is_active=p.is_active) for p in providers]
