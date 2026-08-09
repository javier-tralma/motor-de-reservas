import uuid
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.availability import AvailabilityEngine
from app.models.availability import AvailabilityRule, TimeOff
from app.models.booking import Booking, BookingStatus
from app.models.business import Business
from app.models.provider import Provider, ProviderService
from app.models.service import Service


class AvailabilityService:
    def __init__(self, db: Session, engine: Optional[AvailabilityEngine] = None):
        self.db = db
        self.engine = engine or AvailabilityEngine()

    def get_availability(
        self, business_id: uuid.UUID, service_id: uuid.UUID, target_date: date, provider_id: Optional[uuid.UUID] = None
    ):  # noqa: E501
        # 1. Load Business and Configuration
        business = self.db.execute(select(Business).filter_by(id=business_id)).scalar_one_or_none()
        if not business:
            raise ValueError("Business not found")

        # 2. Load Service
        service = self.db.execute(
            select(Service).filter_by(id=service_id, business_id=business_id, is_active=True)
        ).scalar_one_or_none()  # noqa: E501
        if not service:
            raise ValueError("Service not found or inactive")

        # 3. Load Providers
        provider_query = (
            select(Provider)
            .join(ProviderService)
            .filter(
                Provider.business_id == business_id,
                Provider.is_active.is_(True),
                ProviderService.service_id == service_id,
            )
        )  # noqa: E501
        if provider_id:
            provider_query = provider_query.filter(Provider.id == provider_id)

        providers = self.db.execute(provider_query).scalars().all()
        if not providers:
            return {"timezone": business.timezone, "slots": []}

        provider_ids = [p.id for p in providers]

        # 4. Load Rules for target day
        weekday = target_date.weekday()
        rules = (
            self.db.execute(
                select(AvailabilityRule).filter(
                    AvailabilityRule.business_id == business_id,
                    AvailabilityRule.provider_id.in_(provider_ids),
                    AvailabilityRule.weekday == weekday,
                )  # noqa: E501
            )
            .scalars()
            .all()
        )

        # If no rules at all for this day, fast fail
        if not rules:
            return {"timezone": business.timezone, "slots": []}

        # 5. Load Time Off and Bookings for the window
        # Construimos la ventana UTC exacta del día civil para optimizar consultas de BD
        from app.domain.time_utils import get_local_day_bounds_utc

        window_start_utc, window_end_utc = get_local_day_bounds_utc(target_date, business.timezone)

        time_offs = (
            self.db.execute(
                select(TimeOff).filter(
                    TimeOff.business_id == business_id,
                    TimeOff.provider_id.in_(provider_ids),
                    TimeOff.ends_at > window_start_utc,
                    TimeOff.starts_at < window_end_utc,
                )
            )
            .scalars()
            .all()
        )

        bookings = (
            self.db.execute(
                select(Booking).filter(
                    Booking.business_id == business_id,
                    Booking.provider_id.in_(provider_ids),
                    Booking.status != BookingStatus.cancelled,
                    Booking.ends_at > window_start_utc,
                    Booking.starts_at < window_end_utc,
                )
            )
            .scalars()
            .all()
        )

        # 6. Run Engine
        slots = self.engine.calculate_availability(
            target_date=target_date,
            timezone_str=business.timezone,
            minimum_notice_minutes=business.minimum_booking_notice_minutes,
            horizon_days=business.booking_horizon_days,
            slot_interval_minutes=business.slot_interval_minutes,
            service_duration_minutes=service.duration_minutes,
            rules=rules,
            time_offs=time_offs,
            bookings=bookings,
        )

        return {"timezone": business.timezone, "slots": slots}
