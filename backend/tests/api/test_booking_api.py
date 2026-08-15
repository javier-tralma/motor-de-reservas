import uuid
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.availability import AvailabilityRule
from app.models.booking import Booking
from app.models.business import Business
from app.models.provider import Provider, ProviderService
from app.models.service import Service


def test_booking_api_validation_and_errors(client, db_session):
    b_id = uuid.uuid4()
    p_id = uuid.uuid4()
    s_id = uuid.uuid4()

    business = Business(id=b_id, name="Test B API", slug="test-b-api", email="test@b.com", timezone="America/Santiago")
    provider = Provider(id=p_id, business_id=b_id, name="Test P")
    service = Service(id=s_id, business_id=b_id, name="Test S", duration_minutes=45, price_amount=100)
    ps = ProviderService(business_id=b_id, provider_id=p_id, service_id=s_id)

    target_date = date(2026, 8, 10)
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

    local_tz = ZoneInfo(business.timezone)
    starts_at_local = datetime.combine(target_date, time(10, 0), tzinfo=local_tz)

    base_payload = {
        "service_id": str(service.id),
        "provider_id": str(provider.id),
        "starts_at": starts_at_local.isoformat(),
        "client_request_id": str(uuid.uuid4()),
        "customer_name": "API Test",
        "customer_email": "api@example.com",
        "customer_phone": "+56911111111",
        "customer_notes": "Note",
    }

    original_business_id = settings.BUSINESS_ID
    settings.BUSINESS_ID = business.id

    from datetime import timezone

    from app.api.endpoints.bookings import get_booking_service
    from app.domain.availability import AvailabilityEngine
    from app.integrations.email.service import FakeEmailService
    from app.main import app
    from app.services.availability_service import AvailabilityService
    from app.services.booking_service import BookingService

    def override_booking_service():
        engine = AvailabilityEngine(get_now_fn=lambda tz="UTC": datetime(2026, 8, 1, tzinfo=timezone.utc))
        availability_service = AvailabilityService(db_session, engine=engine)
        return BookingService(db_session, availability_service, FakeEmailService())

    app.dependency_overrides[get_booking_service] = override_booking_service

    try:
        # 1. Validation: extra fields rejected (extra="forbid")
        payload_extra = {**base_payload, "status": "confirmed"}
        r = client.post("/api/public/bookings", json=payload_extra)
        assert r.status_code == 422
        assert "Extra inputs are not permitted" in str(r.json())

        # 2. Validation: blank name rejected
        payload_blank_name = {**base_payload, "customer_name": "   "}
        r = client.post("/api/public/bookings", json=payload_blank_name)
        assert r.status_code == 422
        assert "String should have at least 1 character" in str(r.json())

        # 3. Validation: notes too long
        payload_long_notes = {**base_payload, "customer_notes": "x" * 501}
        r = client.post("/api/public/bookings", json=payload_long_notes)
        assert r.status_code == 422

        # 4. Success: valid payload
        r = client.post("/api/public/bookings", json=base_payload)
        assert r.status_code == 201
        data = r.json()["data"]
        assert "public_reference" in data
        assert data["status"] == "confirmed"
        assert "id" not in data  # No internal IDs in response
        assert "business_id" not in data

        # 5. Idempotency replay
        r_replay = client.post("/api/public/bookings", json=base_payload)
        assert r_replay.status_code == 200
        assert r_replay.json()["data"]["public_reference"] == data["public_reference"]

        # 6. Idempotency conflict (different payload)
        payload_conflict = {**base_payload, "customer_notes": "Different note"}
        r_conflict = client.post("/api/public/bookings", json=payload_conflict)
        assert r_conflict.status_code == 409
        assert r_conflict.json()["error"]["code"] == "idempotency_conflict"

        # 7. Slot unavailable
        payload_unavailable = {**base_payload, "client_request_id": str(uuid.uuid4())}
        r_unav = client.post("/api/public/bookings", json=payload_unavailable)
        assert r_unav.status_code == 409
        assert r_unav.json()["error"]["code"] == "slot_unavailable"

        # 8. Service unavailable
        payload_bad_service = {**base_payload, "service_id": str(uuid.uuid4()), "client_request_id": str(uuid.uuid4())}
        r_bad_serv = client.post("/api/public/bookings", json=payload_bad_service)
        assert r_bad_serv.status_code == 404
        assert r_bad_serv.json()["error"]["code"] == "service_unavailable"

    finally:
        app.dependency_overrides.clear()
        settings.BUSINESS_ID = original_business_id
        db_cleanup = SessionLocal()
        db_cleanup.query(Booking).filter(Booking.business_id == b_id).delete()
        db_cleanup.query(AvailabilityRule).filter(AvailabilityRule.business_id == b_id).delete()
        db_cleanup.query(ProviderService).filter(ProviderService.business_id == b_id).delete()
        db_cleanup.query(Service).filter(Service.business_id == b_id).delete()
        db_cleanup.query(Provider).filter(Provider.business_id == b_id).delete()
        db_cleanup.query(Business).filter(Business.id == b_id).delete()
        db_cleanup.commit()
        db_cleanup.close()


def test_booking_api_default_email_service(client, db_session):
    b_id = uuid.uuid4()
    p_id = uuid.uuid4()
    s_id = uuid.uuid4()

    business = Business(
        id=b_id,
        name="Test Email API Biz",
        slug="test-email-api-biz",
        email="biz@test.cl",
        timezone="America/Santiago",
        address="Calle Central 100",
        phone="+56999887766",
    )
    provider = Provider(id=p_id, business_id=b_id, name="Dr. Default")
    service = Service(id=s_id, business_id=b_id, name="Consulta Email", duration_minutes=30, price_amount=25000)
    ps = ProviderService(business_id=b_id, provider_id=p_id, service_id=s_id)

    target_date = date(2026, 8, 10)
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

    from datetime import timezone

    from app.api.endpoints.bookings import get_booking_service
    from app.domain.availability import AvailabilityEngine
    from app.integrations.email.factory import get_email_service
    from app.main import app
    from app.services.availability_service import AvailabilityService
    from app.services.booking_service import BookingService

    fixed_now = datetime(2026, 8, 1, tzinfo=timezone.utc)
    local_tz = ZoneInfo(business.timezone)
    starts_at_local = datetime.combine(target_date, time(11, 0), tzinfo=local_tz)

    def override_booking_service():
        engine = AvailabilityEngine(get_now_fn=lambda tz="UTC": fixed_now)
        availability_service = AvailabilityService(db_session, engine=engine)
        email_service = get_email_service(settings)
        return BookingService(db_session, availability_service, email_service)

    app.dependency_overrides[get_booking_service] = override_booking_service

    payload = {
        "service_id": str(service.id),
        "provider_id": str(provider.id),
        "starts_at": starts_at_local.isoformat(),
        "client_request_id": str(uuid.uuid4()),
        "customer_name": "Cliente API",
        "customer_email": "cliente@example.com",
        "customer_phone": "+56912345678",
        "customer_notes": "",
    }

    original_business_id = settings.BUSINESS_ID
    settings.BUSINESS_ID = business.id

    try:
        r = client.post("/api/public/bookings", json=payload)
        assert r.status_code == 201
        data = r.json()["data"]
        assert data["status"] == "confirmed"

        # Check in DB that email was processed
        from sqlalchemy import select

        created_booking = db_session.execute(
            select(Booking).filter_by(public_reference=data["public_reference"])
        ).scalar_one()
        assert created_booking.email_delivery_status.value == "sent"
    finally:
        app.dependency_overrides.clear()
        settings.BUSINESS_ID = original_business_id
        db_cleanup = SessionLocal()
        db_cleanup.query(Booking).filter(Booking.business_id == b_id).delete()
        db_cleanup.query(AvailabilityRule).filter(AvailabilityRule.business_id == b_id).delete()
        db_cleanup.query(ProviderService).filter(ProviderService.business_id == b_id).delete()
        db_cleanup.query(Service).filter(Service.business_id == b_id).delete()
        db_cleanup.query(Provider).filter(Provider.business_id == b_id).delete()
        db_cleanup.query(Business).filter(Business.id == b_id).delete()
        db_cleanup.commit()
        db_cleanup.close()
