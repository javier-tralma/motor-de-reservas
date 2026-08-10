import uuid
from datetime import date, datetime, time, timedelta, timezone

import pytest
from sqlalchemy import select

from app.api.endpoints.availability import DomainError
from app.integrations.email.service import EmailDeliveryStatus, FakeEmailService
from app.models.availability import AvailabilityRule
from app.models.booking import Booking, BookingStatus
from app.models.business import Business
from app.models.provider import Provider, ProviderService
from app.models.service import Service
from app.schemas.booking import BookingCreateRequest
from app.services.availability_service import AvailabilityService
from app.services.booking_service import BookingService


class TransactionObservingEmailService(FakeEmailService):
    def __init__(self, db_session):
        super().__init__()
        self.db_session = db_session
        self.was_in_transaction = None

    def send_booking_confirmation(self, data):
        self.was_in_transaction = self.db_session.in_transaction()
        return super().send_booking_confirmation(data)


@pytest.fixture
def fake_email_service(db_session):
    return TransactionObservingEmailService(db_session)


@pytest.fixture
def booking_service(db_session, fake_email_service):
    from datetime import datetime, timezone

    from app.domain.availability import AvailabilityEngine

    # Fixed now time to ensure 2026-08-12 is always in the future
    fixed_now = datetime(2026, 8, 1, tzinfo=timezone.utc)
    engine = AvailabilityEngine(get_now_fn=lambda tz="UTC": fixed_now)
    availability_service = AvailabilityService(db_session, engine=engine)
    return BookingService(db_session, availability_service, fake_email_service)


def test_create_booking_success_specific_provider(db_session, booking_service, fake_email_service):
    b_id = uuid.uuid4()
    p_id = uuid.uuid4()
    s_id = uuid.uuid4()

    business = Business(id=b_id, name="Test B", slug="test-b", email="test@b.com")
    provider = Provider(id=p_id, business_id=b_id, name="Test P")
    service = Service(id=s_id, business_id=b_id, name="Test S", duration_minutes=45, price_amount=100)
    ps = ProviderService(business_id=b_id, provider_id=p_id, service_id=s_id)

    target_date = date(2026, 8, 12)
    rule = AvailabilityRule(
        id=uuid.uuid4(),
        business_id=b_id,
        provider_id=p_id,
        weekday=target_date.weekday(),
        start_time=time(9, 0),
        end_time=time(18, 0),
    )

    db_session.add_all([business, provider, service, ps, rule])
    db_session.commit()

    from zoneinfo import ZoneInfo

    local_tz = ZoneInfo(business.timezone)
    starts_at_local = datetime.combine(target_date, datetime.strptime("10:00", "%H:%M").time(), tzinfo=local_tz)
    starts_at_utc = starts_at_local.astimezone(timezone.utc)

    request = BookingCreateRequest(
        service_id=service.id,
        provider_id=provider.id,
        starts_at=starts_at_utc,
        client_request_id=uuid.uuid4(),
        customer_name="Juan Perez",
        customer_email="juan@example.com",
        customer_phone="+56912345678",
        customer_notes="Nota",
    )

    booking, _ = booking_service.create_public_booking(business.id, request)
    assert booking is not None
    assert booking.status == BookingStatus.confirmed
    assert booking.provider_id == provider.id
    assert booking.email_delivery_status == EmailDeliveryStatus.sent
    assert len(fake_email_service.sent_emails) == 1
    assert fake_email_service.was_in_transaction is False


def test_create_booking_idempotency(db_session, booking_service):
    b_id = uuid.uuid4()
    p_id = uuid.uuid4()
    s_id = uuid.uuid4()

    business = Business(id=b_id, name="Test B", slug="test-b-2", email="test@b.com")
    provider = Provider(id=p_id, business_id=b_id, name="Test P")
    service = Service(id=s_id, business_id=b_id, name="Test S", duration_minutes=45, price_amount=100)
    ps = ProviderService(business_id=b_id, provider_id=p_id, service_id=s_id)

    target_date = date(2026, 8, 12)
    rule = AvailabilityRule(
        id=uuid.uuid4(),
        business_id=b_id,
        provider_id=p_id,
        weekday=target_date.weekday(),
        start_time=time(9, 0),
        end_time=time(18, 0),
    )
    db_session.add_all([business, provider, service, ps, rule])
    db_session.commit()

    from zoneinfo import ZoneInfo

    local_tz = ZoneInfo(business.timezone)
    starts_at_local = datetime.combine(target_date, datetime.strptime("09:00", "%H:%M").time(), tzinfo=local_tz)

    client_request_id = uuid.uuid4()
    request = BookingCreateRequest(
        service_id=service.id,
        provider_id=provider.id,
        starts_at=starts_at_local,
        client_request_id=client_request_id,
        customer_name="Idem",
        customer_email="idem@example.com",
        customer_phone="+56912345678",
    )

    booking1, _ = booking_service.create_public_booking(business.id, request)

    # 2nd call, exactly the same
    booking2, _ = booking_service.create_public_booking(business.id, request)
    assert booking1.id == booking2.id

    # 3rd call, same client_request_id but different time -> conflict
    request.starts_at = starts_at_local + timedelta(hours=1)
    with pytest.raises(DomainError) as exc_info:
        booking_service.create_public_booking(business.id, request)

    assert exc_info.value.code == "idempotency_conflict"
    assert exc_info.value.status_code == 409


def test_create_booking_any_provider(db_session, booking_service):
    b_id = uuid.uuid4()
    p1_id = uuid.uuid4()
    p2_id = uuid.uuid4()
    s_id = uuid.uuid4()

    business = Business(id=b_id, name="Test B", slug="test-b-3", email="test@b.com")
    service = Service(id=s_id, business_id=b_id, name="Test S", duration_minutes=45, price_amount=100)
    provider1 = Provider(id=p1_id, business_id=b_id, name="Test P1")
    provider2 = Provider(id=p2_id, business_id=b_id, name="Test P2")

    ps1 = ProviderService(business_id=b_id, provider_id=p1_id, service_id=s_id)
    ps2 = ProviderService(business_id=b_id, provider_id=p2_id, service_id=s_id)

    target_date = date(2026, 8, 12)
    rule1 = AvailabilityRule(
        id=uuid.uuid4(),
        business_id=b_id,
        provider_id=p1_id,
        weekday=target_date.weekday(),
        start_time=time(9, 0),
        end_time=time(18, 0),
    )
    rule2 = AvailabilityRule(
        id=uuid.uuid4(),
        business_id=b_id,
        provider_id=p2_id,
        weekday=target_date.weekday(),
        start_time=time(9, 0),
        end_time=time(18, 0),
    )

    db_session.add_all([business, service, provider1, provider2, ps1, ps2, rule1, rule2])
    db_session.commit()

    from zoneinfo import ZoneInfo

    local_tz = ZoneInfo(business.timezone)
    starts_at = datetime.combine(target_date, datetime.strptime("09:00", "%H:%M").time(), tzinfo=local_tz)

    request = BookingCreateRequest(
        service_id=service.id,
        provider_id=None,  # Any provider
        starts_at=starts_at,
        client_request_id=uuid.uuid4(),
        customer_name="Any",
        customer_email="any@example.com",
        customer_phone="+56900000000",
    )

    booking, _ = booking_service.create_public_booking(business.id, request)
    assert booking is not None
    assert booking.provider_id in [provider1.id, provider2.id]


def test_email_failure_does_not_rollback(db_session, booking_service, fake_email_service):
    fake_email_service.should_fail = True

    b_id = uuid.uuid4()
    p_id = uuid.uuid4()
    s_id = uuid.uuid4()

    business = Business(id=b_id, name="Test B", slug="test-b-4", email="test@b.com")
    provider = Provider(id=p_id, business_id=b_id, name="Test P")
    service = Service(id=s_id, business_id=b_id, name="Test S", duration_minutes=45, price_amount=100)
    ps = ProviderService(business_id=b_id, provider_id=p_id, service_id=s_id)

    target_date = date(2026, 8, 12)
    rule = AvailabilityRule(
        id=uuid.uuid4(),
        business_id=b_id,
        provider_id=p_id,
        weekday=target_date.weekday(),
        start_time=time(9, 0),
        end_time=time(18, 0),
    )

    db_session.add_all([business, provider, service, ps, rule])
    db_session.commit()

    from zoneinfo import ZoneInfo

    local_tz = ZoneInfo(business.timezone)
    starts_at = datetime.combine(target_date, datetime.strptime("09:00", "%H:%M").time(), tzinfo=local_tz)

    request = BookingCreateRequest(
        service_id=service.id,
        provider_id=provider.id,
        starts_at=starts_at,
        client_request_id=uuid.uuid4(),
        customer_name="Email Fail",
        customer_email="fail@example.com",
        customer_phone="+56900000000",
    )

    booking, _ = booking_service.create_public_booking(business.id, request)
    assert booking is not None
    # Email failed but booking is saved
    assert booking.email_delivery_status == EmailDeliveryStatus.failed

    # Check DB
    db_booking = db_session.execute(select(Booking).filter_by(id=booking.id)).scalar_one()
    assert db_booking.email_delivery_status == EmailDeliveryStatus.failed


def test_email_exception_does_not_rollback(db_session, booking_service, fake_email_service):
    fake_email_service.should_raise = True

    b_id = uuid.uuid4()
    p_id = uuid.uuid4()
    s_id = uuid.uuid4()

    business = Business(id=b_id, name="Test B", slug="test-b-5", email="test@b.com")
    provider = Provider(id=p_id, business_id=b_id, name="Test P")
    service = Service(id=s_id, business_id=b_id, name="Test S", duration_minutes=45, price_amount=100)
    ps = ProviderService(business_id=b_id, provider_id=p_id, service_id=s_id)

    target_date = date(2026, 8, 12)
    rule = AvailabilityRule(
        id=uuid.uuid4(),
        business_id=b_id,
        provider_id=p_id,
        weekday=target_date.weekday(),
        start_time=time(9, 0),
        end_time=time(18, 0),
    )

    db_session.add_all([business, provider, service, ps, rule])
    db_session.commit()

    from zoneinfo import ZoneInfo

    local_tz = ZoneInfo(business.timezone)
    starts_at = datetime.combine(target_date, datetime.strptime("09:00", "%H:%M").time(), tzinfo=local_tz)

    request = BookingCreateRequest(
        service_id=service.id,
        provider_id=provider.id,
        starts_at=starts_at,
        client_request_id=uuid.uuid4(),
        customer_name="Email Fail Exception",
        customer_email="failexc@example.com",
        customer_phone="+56900000000",
    )

    booking, _ = booking_service.create_public_booking(business.id, request)
    assert booking is not None
    # Email failed but booking is saved
    assert booking.email_delivery_status == EmailDeliveryStatus.failed
    assert booking.email_last_error_code == "provider_exception"

    # Check DB
    db_booking = db_session.execute(select(Booking).filter_by(id=booking.id)).scalar_one()
    assert db_booking.email_delivery_status == EmailDeliveryStatus.failed
