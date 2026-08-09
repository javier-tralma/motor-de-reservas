import uuid
from datetime import date, datetime, time, timezone

from app.domain.availability import AvailabilityEngine
from app.models.availability import AvailabilityRule
from app.models.booking import Booking, BookingSource, BookingStatus, EmailDeliveryStatus
from app.models.business import Business
from app.models.provider import Provider, ProviderService
from app.models.service import Service
from app.services.availability_service import AvailabilityService


def test_availability_service_night_boundary(db_session):
    # Test for issue 3: nocturnal timezone window regression check
    b_id = uuid.uuid4()
    p_id = uuid.uuid4()
    s_id = uuid.uuid4()

    business = Business(
        id=b_id,
        name="B Night",
        slug=f"b-night-{uuid.uuid4().hex[:8]}",
        timezone="America/Santiago",
        email="night@b.com",
        minimum_booking_notice_minutes=0,
        booking_horizon_days=30,
        slot_interval_minutes=60,
    )
    provider = Provider(id=p_id, business_id=b_id, name="P Night")
    service = Service(id=s_id, business_id=b_id, name="S Night", duration_minutes=60, price_amount=0)
    rule = AvailabilityRule(
        id=uuid.uuid4(),
        business_id=b_id,
        provider_id=p_id,
        weekday=0,  # Lunes
        start_time=time(21, 0),
        end_time=time(23, 59, 59, 999999),
    )
    ps = ProviderService(provider_id=p_id, service_id=s_id, business_id=b_id)

    db_session.add_all([business, provider, service, rule, ps])
    db_session.commit()

    target_date = date(2026, 8, 10)  # Lunes, winter time, UTC-4

    # 21:00 to 22:00 in America/Santiago is 01:00 to 02:00 UTC (Next Day!)
    booking_start = datetime(2026, 8, 11, 1, 0, tzinfo=timezone.utc)
    booking_end = datetime(2026, 8, 11, 2, 0, tzinfo=timezone.utc)

    booking = Booking(
        id=uuid.uuid4(),
        business_id=b_id,
        provider_id=p_id,
        service_id=s_id,
        public_reference=uuid.uuid4().hex,
        client_request_id=uuid.uuid4(),
        customer_name="Night",
        customer_email="night@test.com",
        customer_phone="123",
        starts_at=booking_start,
        ends_at=booking_end,
        status=BookingStatus.confirmed,
        source=BookingSource.public,
        service_name_snapshot="S",
        duration_minutes_snapshot=60,
        price_amount_snapshot=0,
        provider_name_snapshot="P",
        email_delivery_status=EmailDeliveryStatus.not_requested,
    )
    db_session.add(booking)
    db_session.commit()

    def mock_now(tz="UTC"):
        return datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)

    engine = AvailabilityEngine(get_now_fn=mock_now)
    service_obj = AvailabilityService(db_session, engine=engine)

    res = service_obj.get_availability(b_id, s_id, target_date, provider_id=p_id)

    slots = res["slots"]
    # We expect 22:00, 23:00 to be available. 21:00 is booked (1am UTC next day).
    starts_hours = [s.starts_at.hour for s in slots]

    assert 22 in starts_hours
    assert 21 not in starts_hours  # The booked slot should NOT be available
    assert 23 not in starts_hours  # 23:00 + 60m = 00:00 > 23:59 (rule end)
    assert len(slots) == 1


def test_availability_service_states_and_overlaps(db_session):
    b_id = uuid.uuid4()
    p_id = uuid.uuid4()
    s_id = uuid.uuid4()

    business = Business(
        id=b_id,
        name="B States",
        slug=f"b-states-{uuid.uuid4().hex[:8]}",
        timezone="America/Santiago",
        email="states@b.com",
        minimum_booking_notice_minutes=0,  # removed for this test
        booking_horizon_days=30,
        slot_interval_minutes=60,
    )
    provider = Provider(id=p_id, business_id=b_id, name="P States")
    service = Service(id=s_id, business_id=b_id, name="S States", duration_minutes=60, price_amount=0)

    # Provider works from 10:00 to 18:00
    rule = AvailabilityRule(
        id=uuid.uuid4(),
        business_id=b_id,
        provider_id=p_id,
        weekday=0,  # Lunes
        start_time=time(10, 0),
        end_time=time(18, 0),
    )
    ps = ProviderService(provider_id=p_id, service_id=s_id, business_id=b_id)

    db_session.add_all([business, provider, service, rule, ps])
    db_session.commit()

    target_date = date(2026, 8, 10)  # Lunes

    def mock_now(tz="UTC"):
        return datetime(2026, 8, 10, 9, 30, tzinfo=timezone.utc)

    engine = AvailabilityEngine(get_now_fn=mock_now)
    service_obj = AvailabilityService(db_session, engine=engine)

    def add_booking(start_hour, start_min, end_hour, end_min, status):
        start = datetime(2026, 8, 10, start_hour, start_min, tzinfo=timezone.utc)
        end = datetime(2026, 8, 10, end_hour, end_min, tzinfo=timezone.utc)
        b = Booking(
            id=uuid.uuid4(),
            business_id=b_id,
            provider_id=p_id,
            service_id=s_id,
            public_reference=uuid.uuid4().hex,
            client_request_id=uuid.uuid4(),
            customer_name="Test",
            customer_email="test@test.com",
            customer_phone="123",
            starts_at=start,
            ends_at=end,
            status=status,
            source=BookingSource.public,
            service_name_snapshot="S",
            duration_minutes_snapshot=60,
            price_amount_snapshot=0,
            provider_name_snapshot="P",
            email_delivery_status=EmailDeliveryStatus.not_requested,
        )
        db_session.add(b)
        db_session.commit()

    # In UTC, 10:00 local is 14:00 UTC. 18:00 local is 22:00 UTC.
    # The possible slots are: 14:00-15:00, 15:00-16:00, 16:00-17:00,
    # 17:00-18:00, 18:00-19:00, 19:00-20:00, 20:00-21:00, 21:00-22:00

    # 1. Left partial overlap (blocks 14:00-15:00 UTC)
    add_booking(13, 30, 14, 30, BookingStatus.confirmed)

    # 2. Right partial overlap (blocks 15:00-16:00 UTC)
    add_booking(15, 30, 16, 5, BookingStatus.completed)

    # 3. Candidate contains booking (blocks 16:00-17:00 UTC)
    # The candidate is 16:00-17:00, the booking is 16:10-16:50
    add_booking(16, 10, 16, 50, BookingStatus.confirmed)

    # 4. Cancelled frees (does NOT block 18:00-19:00 UTC)
    add_booking(18, 10, 19, 10, BookingStatus.cancelled)

    res = service_obj.get_availability(b_id, s_id, target_date, provider_id=p_id)
    starts_utc = [s.starts_at.astimezone(timezone.utc).hour for s in res["slots"]]

    # Expected slots not blocked:
    # 14:00 - BLOCKED (overlap)
    # 15:00 - BLOCKED (overlap)
    # 16:00 - BLOCKED (contained in booking)
    # 17:00 - FREE
    # 18:00 - FREE (booking cancelled)
    # 19:00 - FREE
    # 20:00 - FREE
    # 21:00 - FREE

    assert 14 not in starts_utc
    assert 15 not in starts_utc
    assert 16 not in starts_utc
    assert 17 in starts_utc
    assert 18 in starts_utc
    assert 19 in starts_utc
    assert 20 in starts_utc
    assert 21 in starts_utc
    assert len(res["slots"]) == 5


def test_availability_minimum_notice(db_session):
    b_id = uuid.uuid4()
    p_id = uuid.uuid4()
    s_id = uuid.uuid4()

    business = Business(
        id=b_id,
        name="B Notice",
        slug=f"b-notice-{uuid.uuid4().hex[:8]}",
        timezone="America/Santiago",
        email="notice@b.com",
        minimum_booking_notice_minutes=60,
        booking_horizon_days=30,
        slot_interval_minutes=60,
    )
    provider = Provider(id=p_id, business_id=b_id, name="P Notice")
    service = Service(id=s_id, business_id=b_id, name="S Notice", duration_minutes=60, price_amount=0)

    # Provider works from 10:00 to 18:00
    rule = AvailabilityRule(
        id=uuid.uuid4(),
        business_id=b_id,
        provider_id=p_id,
        weekday=0,  # Lunes
        start_time=time(10, 0),
        end_time=time(18, 0),
    )
    ps = ProviderService(provider_id=p_id, service_id=s_id, business_id=b_id)

    db_session.add_all([business, provider, service, rule, ps])
    db_session.commit()

    target_date = date(2026, 8, 10)  # Lunes

    # In UTC, local 10:00 is 14:00 UTC. Slots are 14:00, 15:00, etc.
    # Minimum notice is 60 minutes.

    # Test 1: candidate un minuto antes del límite: excluido
    # Limit is exactly 14:00 UTC.
    # We set now to 13:01 UTC.
    # 13:01 + 60m = 14:01 UTC. 14:00 slot is < 14:01, so it should be EXCLUDED.
    def mock_now_excluded(tz="UTC"):
        return datetime(2026, 8, 10, 13, 1, tzinfo=timezone.utc)

    engine_excluded = AvailabilityEngine(get_now_fn=mock_now_excluded)
    service_obj_excluded = AvailabilityService(db_session, engine=engine_excluded)
    res_excl = service_obj_excluded.get_availability(b_id, s_id, target_date, provider_id=p_id)
    starts_excl = [s.starts_at.astimezone(timezone.utc).hour for s in res_excl["slots"]]
    assert 14 not in starts_excl
    assert 15 in starts_excl  # 15:00 is included

    # Test 2: candidato exactamente en el límite: incluido
    # We set now to 13:00 UTC.
    # 13:00 + 60m = 14:00 UTC. 14:00 slot is >= 14:00, so it should be INCLUDED.
    def mock_now_exact(tz="UTC"):
        return datetime(2026, 8, 10, 13, 0, tzinfo=timezone.utc)

    engine_exact = AvailabilityEngine(get_now_fn=mock_now_exact)
    service_obj_exact = AvailabilityService(db_session, engine=engine_exact)
    res_exact = service_obj_exact.get_availability(b_id, s_id, target_date, provider_id=p_id)
    starts_exact = [s.starts_at.astimezone(timezone.utc).hour for s in res_exact["slots"]]
    assert 14 in starts_exact

    # Test 3: candidato después del límite: incluido
    # We set now to 12:59 UTC.
    # 12:59 + 60m = 13:59 UTC. 14:00 slot is >= 13:59, so it should be INCLUDED.
    def mock_now_after(tz="UTC"):
        return datetime(2026, 8, 10, 12, 59, tzinfo=timezone.utc)

    engine_after = AvailabilityEngine(get_now_fn=mock_now_after)
    service_obj_after = AvailabilityService(db_session, engine=engine_after)
    res_after = service_obj_after.get_availability(b_id, s_id, target_date, provider_id=p_id)
    starts_after = [s.starts_at.astimezone(timezone.utc).hour for s in res_after["slots"]]
    assert 14 in starts_after


def test_availability_business_isolation(db_session):
    # Isolation between two businesses
    b1_id = uuid.uuid4()
    b2_id = uuid.uuid4()

    b1 = Business(
        id=b1_id,
        name="B1",
        slug=f"b1-{uuid.uuid4().hex[:8]}",
        timezone="America/Santiago",
        email="b1@b.com",
        minimum_booking_notice_minutes=0,
        booking_horizon_days=30,
        slot_interval_minutes=60,
    )
    b2 = Business(
        id=b2_id,
        name="B2",
        slug=f"b2-{uuid.uuid4().hex[:8]}",
        timezone="America/Santiago",
        email="b2@b.com",
        minimum_booking_notice_minutes=0,
        booking_horizon_days=30,
        slot_interval_minutes=60,
    )

    p1_id = uuid.uuid4()
    p2_id = uuid.uuid4()
    p1 = Provider(id=p1_id, business_id=b1_id, name="P1")
    p2 = Provider(id=p2_id, business_id=b2_id, name="P2")

    s1_id = uuid.uuid4()
    s2_id = uuid.uuid4()
    s1 = Service(id=s1_id, business_id=b1_id, name="S1", duration_minutes=60, price_amount=0)
    s2 = Service(id=s2_id, business_id=b2_id, name="S2", duration_minutes=60, price_amount=0)

    db_session.add_all([b1, b2, p1, p2, s1, s2])
    db_session.commit()

    # Both have a rule for Lunes 10:00 - 11:00
    db_session.add_all(
        [
            ProviderService(business_id=b1_id, provider_id=p1_id, service_id=s1_id),
            ProviderService(business_id=b2_id, provider_id=p2_id, service_id=s2_id),
            AvailabilityRule(
                id=uuid.uuid4(),
                business_id=b1_id,
                provider_id=p1_id,
                weekday=0,
                start_time=time(10, 0),
                end_time=time(11, 0),
            ),
            AvailabilityRule(
                id=uuid.uuid4(),
                business_id=b2_id,
                provider_id=p2_id,
                weekday=0,
                start_time=time(10, 0),
                end_time=time(11, 0),
            ),
        ]
    )
    db_session.commit()

    # Book the slot for B2
    booking_start = datetime(2026, 8, 10, 14, 0, tzinfo=timezone.utc)
    booking_end = datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc)
    db_session.add(
        Booking(
            id=uuid.uuid4(),
            business_id=b2_id,
            provider_id=p2_id,
            service_id=s2_id,
            public_reference=uuid.uuid4().hex,
            client_request_id=uuid.uuid4(),
            customer_name="Test",
            customer_email="test@test.com",
            customer_phone="123",
            starts_at=booking_start,
            ends_at=booking_end,
            status=BookingStatus.confirmed,
            source=BookingSource.public,
            service_name_snapshot="S",
            duration_minutes_snapshot=60,
            price_amount_snapshot=0,
            provider_name_snapshot="P",
            email_delivery_status=EmailDeliveryStatus.not_requested,
        )
    )
    db_session.commit()

    def mock_now(tz="UTC"):
        return datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)

    engine = AvailabilityEngine(get_now_fn=mock_now)
    service_obj = AvailabilityService(db_session, engine=engine)

    # B1 should have the slot available
    res1 = service_obj.get_availability(b1_id, s1_id, date(2026, 8, 10), provider_id=p1_id)
    assert len(res1["slots"]) == 1

    # B2 should NOT have the slot available
    res2 = service_obj.get_availability(b2_id, s2_id, date(2026, 8, 10), provider_id=p2_id)
    assert len(res2["slots"]) == 0


def test_availability_service_booking_contains_candidate(db_session):
    b_id = uuid.uuid4()
    p_id = uuid.uuid4()
    s_id = uuid.uuid4()

    business = Business(
        id=b_id,
        name="B Contains",
        slug=f"b-contains-{uuid.uuid4().hex[:8]}",
        timezone="America/Santiago",
        email="contains@b.com",
        minimum_booking_notice_minutes=0,
        booking_horizon_days=30,
        slot_interval_minutes=60,
    )
    provider = Provider(id=p_id, business_id=b_id, name="P Contains")
    service = Service(id=s_id, business_id=b_id, name="S Contains", duration_minutes=60, price_amount=0)

    # Provider works from 10:00 to 18:00
    rule = AvailabilityRule(
        id=uuid.uuid4(),
        business_id=b_id,
        provider_id=p_id,
        weekday=0,  # Lunes
        start_time=time(10, 0),
        end_time=time(18, 0),
    )
    ps = ProviderService(provider_id=p_id, service_id=s_id, business_id=b_id)

    db_session.add_all([business, provider, service, rule, ps])
    db_session.commit()

    target_date = date(2026, 8, 10)  # Lunes

    def mock_now(tz="UTC"):
        return datetime(2026, 8, 10, 9, 30, tzinfo=timezone.utc)

    engine = AvailabilityEngine(get_now_fn=mock_now)
    service_obj = AvailabilityService(db_session, engine=engine)

    # Local 10:00 is 14:00 UTC. Slots are 14:00-15:00, 15:00-16:00, etc.
    # We add a booking from 13:30 to 15:30 UTC.
    # This booking contains the 14:00-15:00 slot entirely.

    start = datetime(2026, 8, 10, 13, 30, tzinfo=timezone.utc)
    end = datetime(2026, 8, 10, 15, 30, tzinfo=timezone.utc)
    b = Booking(
        id=uuid.uuid4(),
        business_id=b_id,
        provider_id=p_id,
        service_id=s_id,
        public_reference=uuid.uuid4().hex,
        client_request_id=uuid.uuid4(),
        customer_name="Test",
        customer_email="test@test.com",
        customer_phone="123",
        starts_at=start,
        ends_at=end,
        status=BookingStatus.confirmed,
        source=BookingSource.public,
        service_name_snapshot="S",
        duration_minutes_snapshot=60,
        price_amount_snapshot=0,
        provider_name_snapshot="P",
        email_delivery_status=EmailDeliveryStatus.not_requested,
    )
    db_session.add(b)
    db_session.commit()

    res = service_obj.get_availability(b_id, s_id, target_date, provider_id=p_id)
    starts_utc = [s.starts_at.astimezone(timezone.utc).hour for s in res["slots"]]

    # 14:00-15:00 should be BLOCKED because it's contained inside 13:30-15:30.
    # 15:00-16:00 is also partially blocked (overlaps left), so 15:00 is also blocked.
    # Let's just check 14:00 is not in the list.
    assert 14 not in starts_utc
    assert 15 not in starts_utc
    assert 16 in starts_utc
