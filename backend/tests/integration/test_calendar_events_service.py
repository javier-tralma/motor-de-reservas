import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.api.endpoints.availability import DomainError
from app.domain.time_utils import get_local_day_bounds_utc
from app.integrations.email.service import EmailDeliveryStatus
from app.models.availability import TimeOff
from app.models.booking import Booking, BookingSource, BookingStatus
from app.models.business import Business
from app.models.provider import Provider
from app.models.service import Service
from app.services.calendar_events_service import CalendarEventsService


@pytest.fixture
def calendar_service(db_session: Session) -> CalendarEventsService:
    return CalendarEventsService(db_session)


def test_get_calendar_events_invalid_range_and_too_large(calendar_service: CalendarEventsService, db_session: Session):
    b_id = uuid.uuid4()
    business = Business(id=b_id, name="Test", slug="test", email="t@b.com", timezone="America/Santiago")
    db_session.add(business)
    db_session.commit()

    with pytest.raises(DomainError) as exc:
        calendar_service.get_calendar_events(
            b_id, start_date=date(2026, 1, 2), end_date=date(2026, 1, 1), provider_id=None
        )
    assert exc.value.status_code == 422
    assert exc.value.code == "invalid_date_range"

    with pytest.raises(DomainError) as exc:
        calendar_service.get_calendar_events(
            b_id, start_date=date(2026, 1, 1), end_date=date(2026, 1, 1), provider_id=None
        )
    assert exc.value.status_code == 422
    assert exc.value.code == "invalid_date_range"

    with pytest.raises(DomainError) as exc:
        calendar_service.get_calendar_events(
            b_id, start_date=date(2026, 1, 1), end_date=date(2026, 3, 1), provider_id=None
        )
    assert exc.value.status_code == 422
    assert exc.value.code == "range_too_large"


def test_get_calendar_events_business_not_found(calendar_service: CalendarEventsService):
    with pytest.raises(DomainError) as exc:
        calendar_service.get_calendar_events(
            uuid.uuid4(), start_date=date(2026, 1, 1), end_date=date(2026, 1, 10), provider_id=None
        )
    assert exc.value.status_code == 404
    assert exc.value.code == "business_not_found"


def test_get_calendar_events_provider_not_found_or_foreign(
    calendar_service: CalendarEventsService, db_session: Session
):
    b1_id = uuid.uuid4()
    b2_id = uuid.uuid4()
    db_session.add(Business(id=b1_id, name="B1", slug="b1", email="b1@a.com", timezone="UTC"))
    db_session.add(Business(id=b2_id, name="B2", slug="b2", email="b2@a.com", timezone="UTC"))

    p2_id = uuid.uuid4()
    db_session.add(Provider(id=p2_id, business_id=b2_id, name="P2"))
    db_session.commit()

    with pytest.raises(DomainError) as exc:
        calendar_service.get_calendar_events(
            b1_id, start_date=date(2026, 1, 1), end_date=date(2026, 1, 10), provider_id=p2_id
        )
    assert exc.value.status_code == 404
    assert exc.value.code == "provider_not_found"

    with pytest.raises(DomainError) as exc:
        calendar_service.get_calendar_events(
            b1_id, start_date=date(2026, 1, 1), end_date=date(2026, 1, 10), provider_id=uuid.uuid4()
        )
    assert exc.value.status_code == 404
    assert exc.value.code == "provider_not_found"


def test_get_calendar_events_cross_business_isolation_and_filters(
    calendar_service: CalendarEventsService, db_session: Session
):
    # Business 1
    b1_id = uuid.uuid4()
    b1 = Business(id=b1_id, name="B1", slug="b1", email="b1@a.com", timezone="America/Santiago")
    p1_id = uuid.uuid4()
    p1 = Provider(id=p1_id, business_id=b1_id, name="Provider 1")
    s1_id = uuid.uuid4()
    s1 = Service(id=s1_id, business_id=b1_id, name="S1", duration_minutes=60, price_amount=1000, is_active=True)

    # Business 2
    b2_id = uuid.uuid4()
    b2 = Business(id=b2_id, name="B2", slug="b2", email="b2@b.com", timezone="America/Santiago")
    p2_id = uuid.uuid4()
    p2 = Provider(id=p2_id, business_id=b2_id, name="Provider 2")
    s2_id = uuid.uuid4()
    s2 = Service(id=s2_id, business_id=b2_id, name="S2", duration_minutes=60, price_amount=2000, is_active=True)

    db_session.add_all([b1, b2, p1, p2, s1, s2])
    db_session.commit()

    start_utc, _ = get_local_day_bounds_utc(date(2026, 8, 10), "America/Santiago")

    # B1 booking & timeoff
    b1_booking = Booking(
        business_id=b1_id,
        service_id=s1_id,
        provider_id=p1_id,
        public_reference="B1-BOOK",
        client_request_id=uuid.uuid4(),
        request_fingerprint="fp1",
        customer_name="Cliente B1",
        customer_email="b1@client.com",
        customer_phone="+56911111111",
        starts_at=start_utc + timedelta(hours=10),
        ends_at=start_utc + timedelta(hours=11),
        status=BookingStatus.confirmed,
        source=BookingSource.public,
        service_name_snapshot="S1",
        provider_name_snapshot="Provider 1",
        duration_minutes_snapshot=60,
        price_amount_snapshot=1000,
        email_delivery_status=EmailDeliveryStatus.not_requested,
    )
    b1_timeoff = TimeOff(
        business_id=b1_id,
        provider_id=p1_id,
        starts_at=start_utc + timedelta(hours=14),
        ends_at=start_utc + timedelta(hours=16),
        reason="Bloqueo B1",
    )

    # B2 booking & timeoff (at same exact time)
    b2_booking = Booking(
        business_id=b2_id,
        service_id=s2_id,
        provider_id=p2_id,
        public_reference="B2-BOOK",
        client_request_id=uuid.uuid4(),
        request_fingerprint="fp2",
        customer_name="Cliente B2",
        customer_email="b2@client.com",
        customer_phone="+56922222222",
        starts_at=start_utc + timedelta(hours=10),
        ends_at=start_utc + timedelta(hours=11),
        status=BookingStatus.confirmed,
        source=BookingSource.public,
        service_name_snapshot="S2",
        provider_name_snapshot="Provider 2",
        duration_minutes_snapshot=60,
        price_amount_snapshot=2000,
        email_delivery_status=EmailDeliveryStatus.not_requested,
    )
    b2_timeoff = TimeOff(
        business_id=b2_id,
        provider_id=p2_id,
        starts_at=start_utc + timedelta(hours=14),
        ends_at=start_utc + timedelta(hours=16),
        reason="Bloqueo B2",
    )

    db_session.add_all([b1_booking, b1_timeoff, b2_booking, b2_timeoff])
    db_session.commit()

    # Query B1 with no provider filter
    res_b1_all = calendar_service.get_calendar_events(
        b1_id, start_date=date(2026, 8, 10), end_date=date(2026, 8, 12), provider_id=None
    )
    assert len(res_b1_all.events) == 2
    ids_b1 = {e.id for e in res_b1_all.events}
    assert b1_booking.id in ids_b1
    assert b1_timeoff.id in ids_b1
    assert b2_booking.id not in ids_b1
    assert b2_timeoff.id not in ids_b1

    # Query B1 with provider filter (p1)
    res_b1_p1 = calendar_service.get_calendar_events(
        b1_id, start_date=date(2026, 8, 10), end_date=date(2026, 8, 12), provider_id=p1_id
    )
    assert len(res_b1_p1.events) == 2
    assert {e.id for e in res_b1_p1.events} == {b1_booking.id, b1_timeoff.id}

    # Query B1 with provider from B2 (p2)
    with pytest.raises(DomainError) as exc:
        calendar_service.get_calendar_events(
            b1_id, start_date=date(2026, 8, 10), end_date=date(2026, 8, 12), provider_id=p2_id
        )
    assert exc.value.status_code == 404
    assert exc.value.code == "provider_not_found"


def test_get_calendar_events_all_booking_statuses_and_display_names(
    calendar_service: CalendarEventsService, db_session: Session
):
    b_id = uuid.uuid4()
    business = Business(id=b_id, name="B1", slug="b1", email="b1@a.com", timezone="America/Santiago")
    p_id = uuid.uuid4()
    provider = Provider(id=p_id, business_id=b_id, name="Dra. Valenzuela")
    s_id = uuid.uuid4()
    service = Service(
        id=s_id, business_id=b_id, name="Consulta", duration_minutes=30, price_amount=5000, is_active=True
    )

    db_session.add_all([business, provider, service])
    db_session.commit()

    start_utc, _ = get_local_day_bounds_utc(date(2026, 8, 10), "America/Santiago")

    # Create bookings with each status and varying customer names
    names_and_statuses = [
        ("Maria Jose Perez", BookingStatus.confirmed, 9),
        ("Carlos Silva", BookingStatus.completed, 10),
        ("Camila", BookingStatus.no_show, 11),
        ("Francisca Gonzalez Tapia", BookingStatus.cancelled, 12),
    ]

    bookings = []
    for name, status, hour_offset in names_and_statuses:
        b = Booking(
            business_id=b_id,
            service_id=s_id,
            provider_id=p_id,
            public_reference=f"REF-{hour_offset}",
            client_request_id=uuid.uuid4(),
            request_fingerprint=f"fp-{hour_offset}",
            customer_name=name,
            customer_email="test@test.com",
            customer_phone="+56911111111",
            starts_at=start_utc + timedelta(hours=hour_offset),
            ends_at=start_utc + timedelta(hours=hour_offset, minutes=30),
            status=status,
            source=BookingSource.public,
            service_name_snapshot="Consulta General",
            provider_name_snapshot="Dra. Valenzuela",
            duration_minutes_snapshot=30,
            price_amount_snapshot=5000,
            email_delivery_status=EmailDeliveryStatus.not_requested,
        )
        bookings.append(b)

    db_session.add_all(bookings)
    db_session.commit()

    res = calendar_service.get_calendar_events(
        b_id, start_date=date(2026, 8, 10), end_date=date(2026, 8, 11), provider_id=None
    )
    assert len(res.events) == 4

    ev0, ev1, ev2, ev3 = res.events
    assert ev0.customer_display_name == "Maria P."
    assert ev0.booking_status == "confirmed"
    assert ev0.service_name == "Consulta General"
    assert ev0.provider_name == "Dra. Valenzuela"
    assert ev0.reason is None

    assert ev1.customer_display_name == "Carlos S."
    assert ev1.booking_status == "completed"

    assert ev2.customer_display_name == "Camila"
    assert ev2.booking_status == "no_show"

    assert ev3.customer_display_name == "Francisca T."
    assert ev3.booking_status == "cancelled"


def test_get_calendar_events_past_time_off_and_intersections(
    calendar_service: CalendarEventsService, db_session: Session
):
    b_id = uuid.uuid4()
    business = Business(id=b_id, name="B1", slug="b1", email="b1@a.com", timezone="America/Santiago")
    p_id = uuid.uuid4()
    provider = Provider(id=p_id, business_id=b_id, name="Provider")
    db_session.add_all([business, provider])
    db_session.commit()

    # Range: 2026-08-10 to 2026-08-15
    start_utc, _ = get_local_day_bounds_utc(date(2026, 8, 10), "America/Santiago")
    end_utc, _ = get_local_day_bounds_utc(date(2026, 8, 15), "America/Santiago")

    # 1. Past time off, entirely before range
    t_past_before = TimeOff(
        business_id=b_id,
        provider_id=p_id,
        starts_at=start_utc - timedelta(days=2),
        ends_at=start_utc - timedelta(days=1),
        reason="Past Before",
    )

    # 2. Intersects start boundary: starts before, ends inside range
    t_intersect_start = TimeOff(
        business_id=b_id,
        provider_id=p_id,
        starts_at=start_utc - timedelta(hours=2),
        ends_at=start_utc + timedelta(hours=2),
        reason="Intersect Start",
    )

    # 3. Wholly inside range
    t_inside = TimeOff(
        business_id=b_id,
        provider_id=p_id,
        starts_at=start_utc + timedelta(days=2),
        ends_at=start_utc + timedelta(days=2, hours=4),
        reason="Wholly Inside",
    )

    # 4. Intersects end boundary: starts inside, ends after range
    t_intersect_end = TimeOff(
        business_id=b_id,
        provider_id=p_id,
        starts_at=end_utc - timedelta(hours=2),
        ends_at=end_utc + timedelta(hours=2),
        reason="Intersect End",
    )

    # 5. Wholly after range
    t_after = TimeOff(
        business_id=b_id,
        provider_id=p_id,
        starts_at=end_utc + timedelta(days=1),
        ends_at=end_utc + timedelta(days=2),
        reason="After Range",
    )

    db_session.add_all([t_past_before, t_intersect_start, t_inside, t_intersect_end, t_after])
    db_session.commit()

    res = calendar_service.get_calendar_events(
        b_id, start_date=date(2026, 8, 10), end_date=date(2026, 8, 15), provider_id=None
    )

    # Must only contain 2, 3, 4
    reasons = [e.reason for e in res.events]
    assert "Past Before" not in reasons
    assert "After Range" not in reasons
    assert "Intersect Start" in reasons
    assert "Wholly Inside" in reasons
    assert "Intersect End" in reasons
    assert len(res.events) == 3


def test_get_calendar_events_santiago_dst_offset(calendar_service: CalendarEventsService, db_session: Session):
    b_id = uuid.uuid4()
    business = Business(id=b_id, name="B1", slug="b1", email="b1@a.com", timezone="America/Santiago")
    p_id = uuid.uuid4()
    provider = Provider(id=p_id, business_id=b_id, name="Provider")
    db_session.add_all([business, provider])
    db_session.commit()

    # Winter (Standard Time, UTC-4 in Santiago): August 10, 2026 14:00 UTC = 10:00 local
    t_winter = TimeOff(
        business_id=b_id,
        provider_id=p_id,
        starts_at=datetime(2026, 8, 10, 14, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc),
        reason="Winter",
    )

    # Summer (Daylight Saving Time, UTC-3 in Santiago): December 10, 2026 13:00 UTC = 10:00 local
    t_summer = TimeOff(
        business_id=b_id,
        provider_id=p_id,
        starts_at=datetime(2026, 12, 10, 13, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 12, 10, 14, 0, tzinfo=timezone.utc),
        reason="Summer",
    )

    db_session.add_all([t_winter, t_summer])
    db_session.commit()

    res_winter = calendar_service.get_calendar_events(
        b_id, start_date=date(2026, 8, 10), end_date=date(2026, 8, 11), provider_id=None
    )
    assert len(res_winter.events) == 1
    assert res_winter.events[0].starts_at.isoformat() == "2026-08-10T10:00:00-04:00"

    res_summer = calendar_service.get_calendar_events(
        b_id, start_date=date(2026, 12, 10), end_date=date(2026, 12, 11), provider_id=None
    )
    assert len(res_summer.events) == 1
    assert res_summer.events[0].starts_at.isoformat() == "2026-12-10T10:00:00-03:00"


def test_get_calendar_events_deterministic_sorting(calendar_service: CalendarEventsService, db_session: Session):
    b_id = uuid.uuid4()
    business = Business(id=b_id, name="B1", slug="b1", email="b1@a.com", timezone="America/Santiago")
    p_id = uuid.uuid4()
    provider = Provider(id=p_id, business_id=b_id, name="Provider")
    db_session.add_all([business, provider])
    db_session.commit()

    # Same starts_at for multiple events
    t_base = datetime(2026, 8, 10, 14, 0, tzinfo=timezone.utc)
    t1 = TimeOff(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        business_id=b_id,
        provider_id=p_id,
        starts_at=t_base,
        ends_at=t_base + timedelta(hours=1),
        reason="Event 1",
    )
    t2 = TimeOff(
        id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        business_id=b_id,
        provider_id=p_id,
        starts_at=t_base,
        ends_at=t_base + timedelta(hours=1),
        reason="Event 2",
    )

    db_session.add_all([t2, t1])  # Inserted in reverse order
    db_session.commit()

    res = calendar_service.get_calendar_events(
        b_id, start_date=date(2026, 8, 10), end_date=date(2026, 8, 11), provider_id=None
    )
    assert len(res.events) == 2
    assert res.events[0].id == uuid.UUID("11111111-1111-1111-1111-111111111111")
    assert res.events[1].id == uuid.UUID("22222222-2222-2222-2222-222222222222")
