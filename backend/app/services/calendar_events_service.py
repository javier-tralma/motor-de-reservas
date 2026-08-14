import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.endpoints.availability import DomainError
from app.domain.time_utils import format_local_iso, get_local_day_bounds_utc
from app.models.availability import TimeOff
from app.models.booking import Booking
from app.models.business import Business
from app.models.provider import Provider
from app.schemas.calendar import CalendarEventItem, CalendarEventsData


class CalendarEventsService:
    def __init__(self, db: Session):
        self.db = db

    def get_calendar_events(
        self,
        business_id: uuid.UUID,
        start_date: date,
        end_date: date,
        provider_id: uuid.UUID | None,
    ) -> CalendarEventsData:
        if start_date >= end_date:
            raise DomainError(
                code="invalid_date_range",
                message="Start date must be strictly before end date.",
                status_code=422,
            )

        delta_days = (end_date - start_date).days
        if delta_days > 45:
            raise DomainError(
                code="range_too_large",
                message="Date range exceeds the maximum allowed (45 days).",
                status_code=422,
            )

        business = self.db.execute(select(Business).filter_by(id=business_id)).scalar_one_or_none()
        if not business:
            raise DomainError(code="business_not_found", message="Business not found", status_code=404)

        if provider_id:
            provider = self.db.execute(
                select(Provider).filter_by(id=provider_id, business_id=business_id)
            ).scalar_one_or_none()
            if not provider:
                raise DomainError(
                    code="provider_not_found",
                    message="Provider not found in this business",
                    status_code=404,
                )

        start_utc, _ = get_local_day_bounds_utc(start_date, business.timezone)
        end_utc, _ = get_local_day_bounds_utc(end_date, business.timezone)

        booking_query = select(Booking).filter(
            Booking.business_id == business_id,
            Booking.starts_at < end_utc,
            Booking.ends_at > start_utc,
        )
        if provider_id:
            booking_query = booking_query.filter(Booking.provider_id == provider_id)

        booking_query = booking_query.order_by(Booking.starts_at.asc(), Booking.id.asc())
        bookings = self.db.execute(booking_query).scalars().all()

        timeoff_query = (
            select(TimeOff)
            .join(Provider, TimeOff.provider_id == Provider.id)
            .options(joinedload(TimeOff.provider))
            .filter(
                TimeOff.business_id == business_id,
                TimeOff.starts_at < end_utc,
                TimeOff.ends_at > start_utc,
            )
        )
        if provider_id:
            timeoff_query = timeoff_query.filter(TimeOff.provider_id == provider_id)

        timeoff_query = timeoff_query.order_by(TimeOff.starts_at.asc(), TimeOff.id.asc())
        time_offs = self.db.execute(timeoff_query).scalars().all()

        def _get_customer_display_name(full_name: str) -> str:
            if not full_name:
                return "Desconocido"
            parts = full_name.strip().split()
            if len(parts) == 1:
                return parts[0]
            first = parts[0]
            last = parts[-1]
            return f"{first} {last[0]}."

        events: list[CalendarEventItem] = []

        for b in bookings:
            events.append(
                CalendarEventItem(
                    id=b.id,
                    kind="booking",
                    starts_at=format_local_iso(b.starts_at, business.timezone),
                    ends_at=format_local_iso(b.ends_at, business.timezone),
                    provider_id=b.provider_id,
                    provider_name=b.provider_name_snapshot,
                    booking_status=b.status,
                    customer_display_name=_get_customer_display_name(b.customer_name),
                    service_name=b.service_name_snapshot,
                    reason=None,
                )
            )

        for t in time_offs:
            events.append(
                CalendarEventItem(
                    id=t.id,
                    kind="time_off",
                    starts_at=format_local_iso(t.starts_at, business.timezone),
                    ends_at=format_local_iso(t.ends_at, business.timezone),
                    provider_id=t.provider_id,
                    provider_name=t.provider.name if t.provider else "Desconocido",
                    booking_status=None,
                    customer_display_name=None,
                    service_name=None,
                    reason=t.reason,
                )
            )

        # Merge and sort
        events.sort(key=lambda x: (x.starts_at, str(x.id)))

        return CalendarEventsData(
            timezone=business.timezone,
            events=events,
        )
