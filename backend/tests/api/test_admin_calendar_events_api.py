import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.config import settings
from app.integrations.email.service import EmailDeliveryStatus
from app.models.admin_user import AdminUser
from app.models.availability import TimeOff
from app.models.booking import Booking, BookingSource, BookingStatus
from app.models.business import Business
from app.models.provider import Provider
from app.models.service import Service


def setup_test_data(db: Session, monkeypatch=None):
    biz_id = uuid.uuid4()
    if monkeypatch:
        monkeypatch.setattr(settings, "BUSINESS_ID", str(biz_id))
    else:
        settings.BUSINESS_ID = str(biz_id)

    biz = Business(
        id=biz_id,
        name="Estudio Test",
        slug=f"estudio-{uuid.uuid4().hex[:6]}",
        timezone="America/Santiago",
        locale="es-CL",
        email="contacto@estudio.cl",
    )
    db.add(biz)
    db.commit()

    admin = AdminUser(
        business_id=biz_id,
        email="admin@estudio.cl",
        password_hash=hash_password("Password123!"),
        display_name="Admin",
        is_active=True,
    )
    db.add(admin)
    db.commit()

    return biz, admin


def test_get_calendar_events_unauthorized(client: TestClient):
    resp = client.get("/api/admin/calendar-events?start=2026-08-01&end=2026-08-10")
    assert resp.status_code == 401
    data = resp.json()
    assert "error" in data


def test_get_calendar_events_invalid_query_formats(client: TestClient, db_session: Session, monkeypatch):
    setup_test_data(db_session, monkeypatch)
    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudio.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    # Invalid date format
    resp = client.get("/api/admin/calendar-events?start=invalid-date&end=2026-08-10")
    assert resp.status_code == 422
    data = resp.json()
    assert data["error"]["code"] == "validation_error"
    assert "request_id" in data["error"]

    # Invalid UUID format
    resp = client.get("/api/admin/calendar-events?start=2026-08-01&end=2026-08-10&provider_id=not-a-uuid")
    assert resp.status_code == 422
    data = resp.json()
    assert data["error"]["code"] == "validation_error"
    assert "request_id" in data["error"]

    # start >= end
    resp = client.get("/api/admin/calendar-events?start=2026-08-10&end=2026-08-10")
    assert resp.status_code == 422
    data = resp.json()
    assert data["error"]["code"] == "invalid_date_range"

    # range > 45 days
    resp = client.get("/api/admin/calendar-events?start=2026-01-01&end=2026-03-01")
    assert resp.status_code == 422
    data = resp.json()
    assert data["error"]["code"] == "range_too_large"


def test_get_calendar_events_provider_isolation_and_filter(client: TestClient, db_session: Session, monkeypatch):
    biz, _ = setup_test_data(db_session, monkeypatch)
    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudio.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    # Own provider
    own_provider = Provider(id=uuid.uuid4(), business_id=biz.id, name="Own Provider")
    db_session.add(own_provider)

    # Foreign business and provider
    foreign_biz = Business(
        id=uuid.uuid4(), name="Foreign", slug="foreign", email="f@f.com", timezone="America/Santiago"
    )
    foreign_provider = Provider(id=uuid.uuid4(), business_id=foreign_biz.id, name="Foreign Provider")
    db_session.add(foreign_biz)
    db_session.add(foreign_provider)
    db_session.commit()

    # Query with own provider
    resp_own = client.get(f"/api/admin/calendar-events?start=2026-08-01&end=2026-08-10&provider_id={own_provider.id}")
    assert resp_own.status_code == 200
    assert resp_own.json()["data"]["events"] == []

    # Query with foreign provider -> 404 provider_not_found
    resp_foreign = client.get(
        f"/api/admin/calendar-events?start=2026-08-01&end=2026-08-10&provider_id={foreign_provider.id}"
    )
    assert resp_foreign.status_code == 404
    assert resp_foreign.json()["error"]["code"] == "provider_not_found"


def test_get_calendar_events_api_contract(client: TestClient, db_session: Session, monkeypatch):
    biz, _ = setup_test_data(db_session, monkeypatch)
    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudio.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    provider = Provider(id=uuid.uuid4(), business_id=biz.id, name="Dr. Martin")
    service = Service(
        id=uuid.uuid4(),
        business_id=biz.id,
        name="Consulta VIP",
        duration_minutes=60,
        price_amount=15000,
        is_active=True,
    )
    db_session.add(provider)
    db_session.add(service)
    db_session.commit()

    booking = Booking(
        business_id=biz.id,
        service_id=service.id,
        provider_id=provider.id,
        public_reference="REF-API-1",
        client_request_id=uuid.uuid4(),
        request_fingerprint="fp-api",
        customer_name="Sofia Vergara Lopez",
        customer_email="sofia@test.com",
        customer_phone="+56999999999",
        starts_at=datetime(2026, 8, 10, 14, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc),
        status=BookingStatus.confirmed,
        source=BookingSource.public,
        service_name_snapshot="Consulta VIP",
        provider_name_snapshot="Dr. Martin",
        duration_minutes_snapshot=60,
        price_amount_snapshot=15000,
        email_delivery_status=EmailDeliveryStatus.not_requested,
    )
    time_off = TimeOff(
        business_id=biz.id,
        provider_id=provider.id,
        starts_at=datetime(2026, 8, 11, 14, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 8, 11, 18, 0, tzinfo=timezone.utc),
        reason="Congreso médico",
    )
    db_session.add(booking)
    db_session.add(time_off)
    db_session.commit()

    resp = client.get("/api/admin/calendar-events?start=2026-08-10&end=2026-08-15")
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert data["timezone"] == "America/Santiago"
    events = data["events"]
    assert len(events) == 2

    # Booking event contract
    b_ev = events[0]
    assert b_ev["id"] == str(booking.id)
    assert b_ev["kind"] == "booking"
    assert b_ev["starts_at"] == "2026-08-10T10:00:00-04:00"
    assert b_ev["ends_at"] == "2026-08-10T11:00:00-04:00"
    assert b_ev["provider_id"] == str(provider.id)
    assert b_ev["provider_name"] == "Dr. Martin"
    assert b_ev["booking_status"] == "confirmed"
    assert b_ev["customer_display_name"] == "Sofia L."
    assert b_ev["service_name"] == "Consulta VIP"
    assert b_ev["reason"] is None

    # Time off event contract
    t_ev = events[1]
    assert t_ev["id"] == str(time_off.id)
    assert t_ev["kind"] == "time_off"
    assert t_ev["starts_at"] == "2026-08-11T10:00:00-04:00"
    assert t_ev["ends_at"] == "2026-08-11T14:00:00-04:00"
    assert t_ev["provider_id"] == str(provider.id)
    assert t_ev["provider_name"] == "Dr. Martin"
    assert t_ev["booking_status"] is None
    assert t_ev["customer_display_name"] is None
    assert t_ev["service_name"] is None
    assert t_ev["reason"] == "Congreso médico"
