from datetime import datetime, timezone
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.dependencies import get_current_admin, get_utc_now
from app.domain.time_utils import get_local_day_bounds_utc
from app.models.admin_user import AdminUser
from app.models.booking import Booking, BookingStatus
from app.models.business import Business
from app.schemas.admin import BookingAgendaItem, DashboardData, DashboardResponse, DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["Admin Dashboard"])


@router.get("", response_model=DashboardResponse)
def get_dashboard(
    current_admin: Annotated[AdminUser, Depends(get_current_admin)],
    db: Annotated[Session, Depends(get_db)],
    now: Annotated[datetime, Depends(get_utc_now)],
) -> DashboardResponse:
    business_id = current_admin.business_id
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "business_not_found", "message": "Negocio no encontrado."},
        )

    current_now_utc = now
    if current_now_utc.tzinfo is None:
        current_now_utc = current_now_utc.replace(tzinfo=timezone.utc)
    biz_tz = ZoneInfo(business.timezone)
    now_local = current_now_utc.astimezone(biz_tz)
    today_date = now_local.date()

    start_utc, end_utc = get_local_day_bounds_utc(today_date, business.timezone)

    bookings = (
        db.query(Booking)
        .filter(
            Booking.business_id == business_id,
            Booking.starts_at >= start_utc,
            Booking.starts_at < end_utc,
        )
        .order_by(Booking.starts_at.asc())
        .all()
    )

    total = len(bookings)
    completed = sum(1 for b in bookings if b.status == BookingStatus.completed)
    cancelled = sum(1 for b in bookings if b.status == BookingStatus.cancelled)
    no_show = sum(1 for b in bookings if b.status == BookingStatus.no_show)
    confirmed_remaining = sum(
        1
        for b in bookings
        if b.status == BookingStatus.confirmed
        and (b.starts_at.replace(tzinfo=timezone.utc) if b.starts_at.tzinfo is None else b.starts_at) > current_now_utc
    )

    agenda_items: list[BookingAgendaItem] = []
    next_booking_item: BookingAgendaItem | None = None

    for b in bookings:
        starts_utc = b.starts_at if b.starts_at.tzinfo else b.starts_at.replace(tzinfo=timezone.utc)
        ends_utc = b.ends_at if b.ends_at.tzinfo else b.ends_at.replace(tzinfo=timezone.utc)

        starts_local = starts_utc.astimezone(biz_tz)
        ends_local = ends_utc.astimezone(biz_tz)

        item = BookingAgendaItem(
            id=b.id,
            starts_at=starts_local.isoformat(),
            ends_at=ends_local.isoformat(),
            customer_name=b.customer_name,
            service_name=b.service_name_snapshot,
            provider_name=b.provider_name_snapshot,
            status=b.status.value if hasattr(b.status, "value") else str(b.status),
        )

        agenda_items.append(item)

        if (
            next_booking_item is None
            and (b.status == BookingStatus.confirmed or b.status == "confirmed")
            and starts_utc > current_now_utc
        ):
            next_booking_item = item

    return DashboardResponse(
        data=DashboardData(
            date=today_date.isoformat(),
            timezone=business.timezone,
            summary=DashboardSummary(
                total=total,
                confirmed_remaining=confirmed_remaining,
                completed=completed,
                cancelled=cancelled,
                no_show=no_show,
            ),
            next_booking=next_booking_item,
            agenda=agenda_items,
        )
    )
