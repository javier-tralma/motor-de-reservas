import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.availability import AvailabilityRule, TimeOff
from app.models.booking import Booking, BookingSource, BookingStatus, EmailDeliveryStatus
from app.models.business import Business
from app.models.provider import Provider, ProviderService
from app.models.service import Service
from scripts.seed import run_seed


def test_seed_is_strictly_idempotent(db_session: Session):
    engine = db_session.get_bind()

    # 1. Run seed first time
    run_seed(engine_override=engine)

    b_id = uuid.UUID(str(settings.BUSINESS_ID))
    count_biz_1 = db_session.query(Business).filter(Business.id == b_id).count()
    count_services_1 = db_session.query(Service).filter(Service.business_id == b_id).count()
    count_providers_1 = db_session.query(Provider).filter(Provider.business_id == b_id).count()
    count_ps_1 = db_session.query(ProviderService).filter(ProviderService.business_id == b_id).count()
    count_rules_1 = db_session.query(AvailabilityRule).filter(AvailabilityRule.business_id == b_id).count()
    count_timeoff_1 = db_session.query(TimeOff).filter(TimeOff.business_id == b_id).count()
    count_bookings_1 = db_session.query(Booking).filter(Booking.business_id == b_id).count()

    assert count_biz_1 == 1
    assert count_services_1 == 2
    assert count_providers_1 == 2
    assert count_ps_1 == 3
    assert count_rules_1 == 18
    assert count_timeoff_1 == 1
    assert count_bookings_1 == 6

    # 2. Run seed second time (re-seed)
    run_seed(engine_override=engine)

    count_biz_2 = db_session.query(Business).filter(Business.id == b_id).count()
    count_services_2 = db_session.query(Service).filter(Service.business_id == b_id).count()
    count_providers_2 = db_session.query(Provider).filter(Provider.business_id == b_id).count()
    count_ps_2 = db_session.query(ProviderService).filter(ProviderService.business_id == b_id).count()
    count_rules_2 = db_session.query(AvailabilityRule).filter(AvailabilityRule.business_id == b_id).count()
    count_timeoff_2 = db_session.query(TimeOff).filter(TimeOff.business_id == b_id).count()
    count_bookings_2 = db_session.query(Booking).filter(Booking.business_id == b_id).count()

    assert count_biz_2 == count_biz_1
    assert count_services_2 == count_services_1
    assert count_providers_2 == count_providers_1
    assert count_ps_2 == count_ps_1
    assert count_rules_2 == count_rules_1
    assert count_timeoff_2 == count_timeoff_1
    assert count_bookings_2 == count_bookings_1


def test_seed_preserves_existing_bookings_across_clock_shifts(db_session: Session):
    engine = db_session.get_bind()
    b_id = uuid.UUID(str(settings.BUSINESS_ID))

    # Base clock 1
    base_time_1 = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)
    run_seed(engine_override=engine, now=base_time_1)

    initial_bookings = {
        b.id: (b.starts_at, b.ends_at, b.status, b.customer_name)
        for b in db_session.query(Booking).filter(Booking.business_id == b_id).all()
    }
    assert len(initial_bookings) == 6

    # Add a custom non-demo booking created by a visitor
    custom_booking_id = uuid.uuid4()
    service_id = uuid.UUID("00000000-0000-0000-0000-000000000101")
    provider_id = uuid.UUID("00000000-0000-0000-0000-000000000201")
    custom_start = datetime(2026, 8, 20, 10, 0, tzinfo=timezone.utc)
    custom_end = datetime(2026, 8, 20, 10, 45, tzinfo=timezone.utc)

    custom_booking = Booking(
        id=custom_booking_id,
        business_id=b_id,
        service_id=service_id,
        provider_id=provider_id,
        public_reference="VISITOR-REF-999",
        customer_name="Cliente Real",
        customer_email="cliente.real@example.com",
        customer_phone="+56998887766",
        starts_at=custom_start,
        ends_at=custom_end,
        status=BookingStatus.confirmed,
        source=BookingSource.public,
        service_name_snapshot="Corte de Cabello",
        duration_minutes_snapshot=45,
        price_amount_snapshot=15000,
        provider_name_snapshot="Camila Rojas",
        email_delivery_status=EmailDeliveryStatus.not_requested,
    )
    db_session.add(custom_booking)
    db_session.commit()

    # Re-run seed with Clock shifted 14 days into the future (simulating restart after 2 weeks)
    base_time_2 = base_time_1 + timedelta(days=14)
    run_seed(engine_override=engine, now=base_time_2)

    after_bookings = {
        b.id: (b.starts_at, b.ends_at, b.status, b.customer_name)
        for b in db_session.query(Booking).filter(Booking.business_id == b_id).all()
    }

    # Total must be 6 demo + 1 custom visitor = 7 bookings
    assert len(after_bookings) == 7

    # All initial demo bookings must preserve their EXACT timestamps and intervals
    for b_id_key, initial_vals in initial_bookings.items():
        assert after_bookings[b_id_key] == initial_vals

    # Custom booking is completely untouched
    assert custom_booking_id in after_bookings
    assert after_bookings[custom_booking_id] == (custom_start, custom_end, BookingStatus.confirmed, "Cliente Real")


def test_seed_production_validation_fails_without_credentials(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "ADMIN_EMAIL", "")
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", "")

    with pytest.raises(ValueError, match="ADMIN_EMAIL y ADMIN_PASSWORD deben estar configurados"):
        run_seed()


def test_seed_bookings_contain_no_real_pii(db_session: Session):
    engine = db_session.get_bind()
    run_seed(engine_override=engine)

    b_id = uuid.UUID(str(settings.BUSINESS_ID))
    bookings = db_session.query(Booking).filter(Booking.business_id == b_id).all()

    for booking in bookings:
        # All customer emails must use reserved test domains
        assert booking.customer_email.endswith("@example.com")
        # Email delivery status must accurately reflect that no email was sent
        assert booking.email_delivery_status == EmailDeliveryStatus.not_requested
        # Snapshots must be populated
        assert booking.service_name_snapshot in ("Corte de Cabello", "Barba Spa")
        assert booking.provider_name_snapshot in ("Camila Rojas", "Javier Pérez")
        assert booking.duration_minutes_snapshot > 0
        assert booking.price_amount_snapshot > 0
