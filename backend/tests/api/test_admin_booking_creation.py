import uuid
from datetime import datetime, time, timezone
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.admin.bookings import get_booking_service_admin
from app.core.auth import hash_password
from app.core.config import settings
from app.domain.availability import AvailabilityEngine
from app.integrations.email.service import FakeEmailService, NoOpEmailService
from app.main import app
from app.models.admin_user import AdminUser
from app.models.availability import AvailabilityRule, TimeOff
from app.models.booking import Booking, BookingSource, BookingStatus, EmailDeliveryStatus
from app.models.business import Business
from app.models.provider import Provider, ProviderService
from app.models.service import Service
from app.services.availability_service import AvailabilityService
from app.services.booking_service import BookingService

FIXED_NOW = datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def override_booking_service_admin(db_session: Session):
    engine = AvailabilityEngine(get_now_fn=lambda tz="UTC": FIXED_NOW)
    availability_service = AvailabilityService(db_session, engine=engine)
    email_service = NoOpEmailService()
    booking_service = BookingService(db_session, availability_service, email_service)

    app.dependency_overrides[get_booking_service_admin] = lambda: booking_service
    try:
        yield booking_service
    finally:
        app.dependency_overrides.pop(get_booking_service_admin, None)


def setup_admin_booking_test_data(db: Session, monkeypatch):
    monkeypatch.setattr("app.domain.time_utils.get_now", lambda tz=timezone.utc: FIXED_NOW)

    biz_id = uuid.uuid4()
    monkeypatch.setattr(settings, "BUSINESS_ID", str(biz_id))

    biz = Business(
        id=biz_id,
        name="Test Biz",
        slug=f"test-biz-{uuid.uuid4().hex[:8]}",
        timezone="America/Santiago",
        locale="es-CL",
        email="test@biz.com",
    )
    db.add(biz)
    db.flush()

    admin = AdminUser(
        business_id=biz_id,
        email="admin@test.com",
        password_hash=hash_password("Pass123!"),
        display_name="Admin",
        is_active=True,
    )
    db.add(admin)

    service = Service(
        id=uuid.uuid4(),
        business_id=biz_id,
        name="Test Service",
        duration_minutes=60,
        price_amount=1000,
        is_active=True,
    )
    db.add(service)

    provider = Provider(
        id=uuid.uuid4(),
        business_id=biz_id,
        name="Test Provider",
        is_active=True,
    )
    db.add(provider)
    db.commit()

    db.add(ProviderService(business_id=biz_id, provider_id=provider.id, service_id=service.id))

    # Add a weekly rule that covers Monday 09:00 - 18:00
    rule = AvailabilityRule(
        business_id=biz_id,
        provider_id=provider.id,
        weekday=0,  # Monday
        start_time=time(9, 0),
        end_time=time(18, 0),
    )
    db.add(rule)
    db.commit()

    return biz_id, admin.email, service.id, provider.id


def test_create_admin_booking_success(
    client: TestClient, db_session: Session, monkeypatch, override_booking_service_admin
):
    biz_id, admin_email, svc_id, prov_id = setup_admin_booking_test_data(db_session, monkeypatch)

    client.post(
        "/api/admin/auth/login",
        json={"email": admin_email, "password": "Pass123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    client_request_id = str(uuid.uuid4())
    local_tz = ZoneInfo("America/Santiago")
    target_date = datetime(2026, 8, 17).date()
    starts_at = datetime.combine(target_date, time(10, 0), tzinfo=local_tz).isoformat()

    payload = {
        "service_id": str(svc_id),
        "provider_id": str(prov_id),
        "starts_at": starts_at,
        "client_request_id": client_request_id,
        "customer_name": "New Customer",
        "customer_email": "new@customer.com",
        "customer_phone": "+56912345678",
        "customer_notes": "Admin booking notes",
    }

    res = client.post(
        "/api/admin/bookings",
        json=payload,
        headers={"Origin": settings.FRONTEND_URL},
    )

    assert res.status_code == 201, res.json()
    data = res.json()["data"]
    assert data["customer_name"] == "New Customer"
    assert data["source"] == BookingSource.admin.value
    assert data["status"] == BookingStatus.confirmed.value

    # Admin response does not expose internal email delivery fields
    assert "email_delivery_status" not in data
    assert "email_provider_id" not in data
    assert "email_sent_at" not in data
    assert "email_last_error_code" not in data

    # Verify in DB
    booking = db_session.query(Booking).filter_by(id=data["id"]).first()
    assert booking.email_delivery_status == EmailDeliveryStatus.not_requested
    assert booking.source == BookingSource.admin
    assert booking.client_request_id == uuid.UUID(client_request_id)


def test_create_admin_booking_idempotency(
    client: TestClient, db_session: Session, monkeypatch, override_booking_service_admin
):
    biz_id, admin_email, svc_id, prov_id = setup_admin_booking_test_data(db_session, monkeypatch)

    client.post(
        "/api/admin/auth/login",
        json={"email": admin_email, "password": "Pass123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    client_request_id = str(uuid.uuid4())
    local_tz = ZoneInfo("America/Santiago")
    target_date = datetime(2026, 8, 17).date()
    starts_at = datetime.combine(target_date, time(10, 0), tzinfo=local_tz).isoformat()

    payload = {
        "service_id": str(svc_id),
        "provider_id": str(prov_id),
        "starts_at": starts_at,
        "client_request_id": client_request_id,
        "customer_name": "Idempotent Customer",
        "customer_email": "new@customer.com",
        "customer_phone": "+56912345678",
        "customer_notes": "",
    }

    # First request
    res1 = client.post("/api/admin/bookings", json=payload, headers={"Origin": settings.FRONTEND_URL})
    assert res1.status_code == 201

    # Second request (replay)
    res2 = client.post("/api/admin/bookings", json=payload, headers={"Origin": settings.FRONTEND_URL})
    assert res2.status_code == 200
    assert res1.json()["data"]["id"] == res2.json()["data"]["id"]

    # Third request with same UUID but modified payload
    payload_modified = {**payload, "customer_name": "Another Name"}
    res3 = client.post("/api/admin/bookings", json=payload_modified, headers={"Origin": settings.FRONTEND_URL})
    assert res3.status_code == 409
    assert res3.json()["error"]["code"] == "idempotency_conflict"


def test_create_admin_booking_strict_payload(
    client: TestClient, db_session: Session, monkeypatch, override_booking_service_admin
):
    biz_id, admin_email, svc_id, prov_id = setup_admin_booking_test_data(db_session, monkeypatch)

    client.post(
        "/api/admin/auth/login",
        json={"email": admin_email, "password": "Pass123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    local_tz = ZoneInfo("America/Santiago")
    target_date = datetime(2026, 8, 17).date()
    starts_at = datetime.combine(target_date, time(10, 0), tzinfo=local_tz).isoformat()

    payload = {
        "service_id": str(svc_id),
        "provider_id": str(prov_id),
        "starts_at": starts_at,
        "client_request_id": str(uuid.uuid4()),
        "customer_name": "Name",
        "customer_email": "new@customer.com",
        "customer_phone": "+56912345678",
        "customer_notes": "",
        "status": "cancelled",  # EXTRA FIELD
    }

    res = client.post("/api/admin/bookings", json=payload, headers={"Origin": settings.FRONTEND_URL})
    assert res.status_code == 422


def test_create_admin_booking_no_email_sent(client: TestClient, db_session: Session, monkeypatch):
    biz_id, admin_email, svc_id, prov_id = setup_admin_booking_test_data(db_session, monkeypatch)

    mock_email_service = MagicMock(spec=FakeEmailService)
    engine = AvailabilityEngine(get_now_fn=lambda tz="UTC": FIXED_NOW)
    availability_service = AvailabilityService(db_session, engine=engine)
    booking_service = BookingService(db_session, availability_service, mock_email_service)

    app.dependency_overrides[get_booking_service_admin] = lambda: booking_service

    try:
        client.post(
            "/api/admin/auth/login",
            json={"email": admin_email, "password": "Pass123!"},
            headers={"Origin": settings.FRONTEND_URL},
        )

        local_tz = ZoneInfo("America/Santiago")
        target_date = datetime(2026, 8, 17).date()
        starts_at = datetime.combine(target_date, time(10, 0), tzinfo=local_tz).isoformat()

        payload = {
            "service_id": str(svc_id),
            "provider_id": str(prov_id),
            "starts_at": starts_at,
            "client_request_id": str(uuid.uuid4()),
            "customer_name": "Name",
            "customer_email": "new@customer.com",
            "customer_phone": "+56912345678",
            "customer_notes": "",
        }

        res = client.post("/api/admin/bookings", json=payload, headers={"Origin": settings.FRONTEND_URL})
        assert res.status_code == 201

        # Assert zero calls to EmailService
        mock_email_service.send_booking_confirmation.assert_not_called()
    finally:
        app.dependency_overrides.pop(get_booking_service_admin, None)


def test_create_admin_booking_auth_and_csrf_missing(
    client: TestClient, db_session: Session, monkeypatch, override_booking_service_admin
):
    biz_id, admin_email, svc_id, prov_id = setup_admin_booking_test_data(db_session, monkeypatch)

    payload = {
        "service_id": str(svc_id),
        "provider_id": str(prov_id),
        "starts_at": "2026-08-17T10:00:00-04:00",
        "client_request_id": str(uuid.uuid4()),
        "customer_name": "Name",
        "customer_email": "new@customer.com",
        "customer_phone": "+56912345678",
        "customer_notes": "",
    }

    # No auth, no CSRF Origin -> 401
    res1 = client.post("/api/admin/bookings", json=payload)
    assert res1.status_code == 401

    # Auth but no CSRF Origin -> 403
    client.post(
        "/api/admin/auth/login",
        json={"email": admin_email, "password": "Pass123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )
    res2 = client.post("/api/admin/bookings", json=payload)
    assert res2.status_code == 403


def test_create_admin_booking_domain_rules(
    client: TestClient, db_session: Session, monkeypatch, override_booking_service_admin
):
    biz_id, admin_email, svc_id, prov_id = setup_admin_booking_test_data(db_session, monkeypatch)

    client.post(
        "/api/admin/auth/login",
        json={"email": admin_email, "password": "Pass123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    local_tz = ZoneInfo("America/Santiago")
    target_date = datetime(2026, 8, 17).date()
    # Monday 09:00-18:00 is available

    base_payload = {
        "service_id": str(svc_id),
        "provider_id": str(prov_id),
        "customer_name": "Name",
        "customer_email": "new@customer.com",
        "customer_phone": "+56912345678",
        "customer_notes": "",
    }

    # 1. Outside rule (08:00)
    out_payload = {
        **base_payload,
        "starts_at": datetime.combine(target_date, time(8, 0), tzinfo=local_tz).isoformat(),
        "client_request_id": str(uuid.uuid4()),
    }
    res1 = client.post("/api/admin/bookings", json=out_payload, headers={"Origin": settings.FRONTEND_URL})
    assert res1.status_code == 409

    # 2. Inactive provider
    p2 = Provider(id=uuid.uuid4(), business_id=biz_id, name="Test Provider 2", is_active=False)
    db_session.add(p2)
    db_session.add(ProviderService(business_id=biz_id, provider_id=p2.id, service_id=svc_id))
    db_session.commit()
    inact_prov_payload = {
        **base_payload,
        "provider_id": str(p2.id),
        "starts_at": datetime.combine(target_date, time(10, 0), tzinfo=local_tz).isoformat(),
        "client_request_id": str(uuid.uuid4()),
    }
    res2 = client.post("/api/admin/bookings", json=inact_prov_payload, headers={"Origin": settings.FRONTEND_URL})
    assert res2.status_code == 409

    # 3. Missing ProviderService relationship
    p3 = Provider(id=uuid.uuid4(), business_id=biz_id, name="Test Provider 3", is_active=True)
    db_session.add(p3)
    db_session.commit()
    # No ProviderService
    no_ps_payload = {
        **base_payload,
        "provider_id": str(p3.id),
        "starts_at": datetime.combine(target_date, time(10, 0), tzinfo=local_tz).isoformat(),
        "client_request_id": str(uuid.uuid4()),
    }
    res3 = client.post("/api/admin/bookings", json=no_ps_payload, headers={"Origin": settings.FRONTEND_URL})
    assert res3.status_code == 409

    # 4. Overlap with cancelled -> ok, then overlap with confirmed -> 409
    starts_11 = datetime.combine(target_date, time(11, 0), tzinfo=local_tz).isoformat()
    # Cancelled first
    payload_can = {**base_payload, "starts_at": starts_11, "client_request_id": str(uuid.uuid4())}
    res_can = client.post("/api/admin/bookings", json=payload_can, headers={"Origin": settings.FRONTEND_URL})
    assert res_can.status_code == 201
    db_session.query(Booking).filter_by(id=res_can.json()["data"]["id"]).update({"status": BookingStatus.cancelled})
    db_session.commit()
    # Now confirmed
    payload_conf = {**base_payload, "starts_at": starts_11, "client_request_id": str(uuid.uuid4())}
    res_conf = client.post("/api/admin/bookings", json=payload_conf, headers={"Origin": settings.FRONTEND_URL})
    assert res_conf.status_code == 201
    # Another overlapping
    payload_overlap = {**base_payload, "starts_at": starts_11, "client_request_id": str(uuid.uuid4())}
    res_overlap = client.post("/api/admin/bookings", json=payload_overlap, headers={"Origin": settings.FRONTEND_URL})
    assert res_overlap.status_code == 409


def test_create_admin_booking_extended_domain_rules(
    client: TestClient, db_session: Session, monkeypatch, override_booking_service_admin
):
    from datetime import timedelta

    biz_id, admin_email, svc_id, prov_id = setup_admin_booking_test_data(db_session, monkeypatch)

    # Setup other business
    other_biz_id = uuid.uuid4()
    other_biz = Business(
        id=other_biz_id,
        name="Other Biz",
        slug=f"other-{uuid.uuid4().hex[:8]}",
        timezone="America/Santiago",
        email="other@test.com",
    )
    db_session.add(other_biz)

    other_svc_id = uuid.uuid4()
    other_svc = Service(
        id=other_svc_id, business_id=other_biz_id, name="Other Svc", duration_minutes=30, price_amount=100
    )
    db_session.add(other_svc)
    db_session.commit()

    client.post(
        "/api/admin/auth/login",
        json={"email": admin_email, "password": "Pass123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    local_tz = ZoneInfo("America/Santiago")
    target_date = datetime(2026, 8, 17).date()  # Monday
    base_payload = {
        "service_id": str(svc_id),
        "provider_id": str(prov_id),
        "customer_name": "Name",
        "customer_email": "new@customer.com",
        "customer_phone": "+56912345678",
        "customer_notes": "",
    }

    # 1. client_request_id omitido e inválido -> 422
    starts_10 = datetime.combine(target_date, time(10, 0), tzinfo=local_tz).isoformat()
    res_omit = client.post(
        "/api/admin/bookings", json={**base_payload, "starts_at": starts_10}, headers={"Origin": settings.FRONTEND_URL}
    )
    assert res_omit.status_code == 422
    assert "error" in res_omit.json()

    res_inv = client.post(
        "/api/admin/bookings",
        json={**base_payload, "starts_at": starts_10, "client_request_id": "not-a-uuid"},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_inv.status_code == 422
    assert "error" in res_inv.json()

    # 2. time_off solapado -> 409 slot_unavailable
    starts_11 = datetime.combine(target_date, time(11, 0), tzinfo=local_tz)
    to = TimeOff(
        id=uuid.uuid4(),
        business_id=biz_id,
        provider_id=prov_id,
        starts_at=starts_11,
        ends_at=starts_11 + timedelta(hours=1),
    )
    db_session.add(to)
    db_session.commit()

    res_to = client.post(
        "/api/admin/bookings",
        json={**base_payload, "starts_at": starts_11.isoformat(), "client_request_id": str(uuid.uuid4())},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_to.status_code == 409
    assert res_to.json()["error"]["code"] == "slot_unavailable"

    # 3. reservas completed y no_show bloquean
    starts_13 = datetime.combine(target_date, time(13, 0), tzinfo=local_tz)
    b_completed = Booking(
        id=uuid.uuid4(),
        business_id=biz_id,
        provider_id=prov_id,
        service_id=svc_id,
        starts_at=starts_13,
        ends_at=starts_13 + timedelta(minutes=60),
        status=BookingStatus.completed,
        customer_name="N",
        customer_email="e@e.com",
        customer_phone="+123",
        source="admin",
        public_reference="REF-C",
        client_request_id=uuid.uuid4(),
        request_fingerprint="fp1",
        service_name_snapshot="Svc",
        duration_minutes_snapshot=60,
        price_amount_snapshot=0,
        provider_name_snapshot="Prov",
        email_delivery_status="not_requested",
    )
    db_session.add(b_completed)
    db_session.commit()

    res_comp = client.post(
        "/api/admin/bookings",
        json={**base_payload, "starts_at": starts_13.isoformat(), "client_request_id": str(uuid.uuid4())},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_comp.status_code == 409

    starts_14 = datetime.combine(target_date, time(14, 0), tzinfo=local_tz)
    b_noshow = Booking(
        id=uuid.uuid4(),
        business_id=biz_id,
        provider_id=prov_id,
        service_id=svc_id,
        starts_at=starts_14,
        ends_at=starts_14 + timedelta(minutes=60),
        status=BookingStatus.no_show,
        customer_name="N",
        customer_email="e@e.com",
        customer_phone="+123",
        source="admin",
        public_reference="REF-N",
        client_request_id=uuid.uuid4(),
        request_fingerprint="fp2",
        service_name_snapshot="Svc",
        duration_minutes_snapshot=60,
        price_amount_snapshot=0,
        provider_name_snapshot="Prov",
        email_delivery_status="not_requested",
    )
    db_session.add(b_noshow)
    db_session.commit()

    res_noshow = client.post(
        "/api/admin/bookings",
        json={**base_payload, "starts_at": starts_14.isoformat(), "client_request_id": str(uuid.uuid4())},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_noshow.status_code == 409

    # 4. servicio inactivo -> error
    inactive_svc_id = uuid.uuid4()
    inactive_svc = Service(
        id=inactive_svc_id, business_id=biz_id, name="Inact Svc", duration_minutes=30, price_amount=100, is_active=False
    )
    db_session.add(inactive_svc)
    db_session.commit()

    res_inact = client.post(
        "/api/admin/bookings",
        json={
            **base_payload,
            "service_id": str(inactive_svc_id),
            "starts_at": starts_10,
            "client_request_id": str(uuid.uuid4()),
        },
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_inact.status_code == 404

    # 5. recurso de otro negocio -> 404
    res_other = client.post(
        "/api/admin/bookings",
        json={
            **base_payload,
            "service_id": str(other_svc_id),
            "starts_at": starts_10,
            "client_request_id": str(uuid.uuid4()),
        },
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_other.status_code == 404

    # 6. adyacencia permitida
    starts_15 = datetime.combine(target_date, time(15, 0), tzinfo=local_tz)
    b_15 = Booking(
        id=uuid.uuid4(),
        business_id=biz_id,
        provider_id=prov_id,
        service_id=svc_id,
        starts_at=starts_15,
        ends_at=starts_15 + timedelta(minutes=60),
        status=BookingStatus.confirmed,
        customer_name="N",
        customer_email="e@e.com",
        customer_phone="+123",
        source="admin",
        public_reference="REF-A",
        client_request_id=uuid.uuid4(),
        request_fingerprint="fp3",
        service_name_snapshot="Svc",
        duration_minutes_snapshot=60,
        price_amount_snapshot=0,
        provider_name_snapshot="Prov",
        email_delivery_status="not_requested",
    )
    db_session.add(b_15)
    db_session.commit()

    starts_16 = datetime.combine(target_date, time(16, 0), tzinfo=local_tz)
    res_adj = client.post(
        "/api/admin/bookings",
        json={**base_payload, "starts_at": starts_16.isoformat(), "client_request_id": str(uuid.uuid4())},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_adj.status_code == 201

    # 7. respuesta admin no expone email_delivery_status
    data = res_adj.json()["data"]
    assert "email_delivery_status" not in data
    assert "email_delivered_at" not in data
    assert "email_error" not in data


def test_create_admin_booking_independent_of_system_clock(client: TestClient, db_session: Session, monkeypatch):
    """Demuestra explícitamente que la validez del slot en POST /api/admin/bookings

    depende únicamente del reloj inyectado en AvailabilityEngine y no de la fecha real del sistema.
    """
    biz_id, admin_email, svc_id, prov_id = setup_admin_booking_test_data(db_session, monkeypatch)

    client.post(
        "/api/admin/auth/login",
        json={"email": admin_email, "password": "Pass123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    local_tz = ZoneInfo("America/Santiago")
    # Elegimos una fecha fija en el futuro (2035-10-15 es lunes, weekday 0)
    future_date = datetime(2035, 10, 15).date()
    assert future_date.weekday() == 0

    slot_time = datetime.combine(future_date, time(10, 0), tzinfo=local_tz)
    payload = {
        "service_id": str(svc_id),
        "provider_id": str(prov_id),
        "starts_at": slot_time.isoformat(),
        "client_request_id": str(uuid.uuid4()),
        "customer_name": "Clock Test Customer",
        "customer_email": "clock@test.com",
        "customer_phone": "+56912345678",
        "customer_notes": "",
    }

    # 1. Con un reloj inyectado anterior al slot (2035-10-01), la reserva es válida y se crea (201)
    clock_before = datetime(2035, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    engine_before = AvailabilityEngine(get_now_fn=lambda tz="UTC": clock_before)
    service_before = BookingService(
        db_session, AvailabilityService(db_session, engine=engine_before), NoOpEmailService()
    )

    app.dependency_overrides[get_booking_service_admin] = lambda: service_before
    try:
        res1 = client.post("/api/admin/bookings", json=payload, headers={"Origin": settings.FRONTEND_URL})
        assert res1.status_code == 201, res1.json()
        assert res1.json()["data"]["customer_name"] == "Clock Test Customer"
    finally:
        app.dependency_overrides.pop(get_booking_service_admin, None)

    # 2. Con un reloj inyectado posterior al slot (2035-10-20), el slot es pasado y es rechazado (409 slot_unavailable)
    clock_after = datetime(2035, 10, 20, 12, 0, 0, tzinfo=timezone.utc)
    engine_after = AvailabilityEngine(get_now_fn=lambda tz="UTC": clock_after)
    service_after = BookingService(db_session, AvailabilityService(db_session, engine=engine_after), NoOpEmailService())

    payload_new_id = {**payload, "client_request_id": str(uuid.uuid4())}
    app.dependency_overrides[get_booking_service_admin] = lambda: service_after
    try:
        res2 = client.post("/api/admin/bookings", json=payload_new_id, headers={"Origin": settings.FRONTEND_URL})
        assert res2.status_code == 409
        assert res2.json()["error"]["code"] == "slot_unavailable"
    finally:
        app.dependency_overrides.pop(get_booking_service_admin, None)


def test_create_admin_booking_concurrency(monkeypatch):
    import threading

    from sqlalchemy import text

    from app.api.endpoints.availability import DomainError
    from app.core.db import SessionLocal

    db_setup = SessionLocal()
    biz_id, admin_email, svc_id, prov_id = setup_admin_booking_test_data(db_setup, monkeypatch)
    db_setup.commit()

    try:
        local_tz = ZoneInfo("America/Santiago")
        target_date = datetime(2026, 8, 17).date()
        starts_at = datetime.combine(target_date, time(12, 0), tzinfo=local_tz).isoformat()

        barrier = threading.Barrier(2, timeout=5.0)
        results = [None, None]

        def make_request(thread_idx):
            local_db = SessionLocal()
            try:
                engine = AvailabilityEngine(get_now_fn=lambda tz="UTC": FIXED_NOW)
                availability_service = AvailabilityService(local_db, engine=engine)
                email_service = FakeEmailService()
                booking_service = BookingService(local_db, availability_service, email_service)

                from app.schemas.booking_admin import AdminBookingCreateRequest

                req = AdminBookingCreateRequest(
                    service_id=svc_id,
                    provider_id=prov_id,
                    starts_at=datetime.fromisoformat(starts_at),
                    client_request_id=uuid.uuid4(),
                    customer_name="Name",
                    customer_email="new@customer.com",
                    customer_phone="+56912345678",
                    customer_notes="",
                )

                barrier.wait(timeout=5.0)
                booking_service.create_admin_booking(biz_id, req)
                results[thread_idx] = "SUCCESS"
            except DomainError as e:
                if e.code == "slot_unavailable":
                    results[thread_idx] = "CONFLICT"
                else:
                    results[thread_idx] = f"ERROR: {e.code}"
            except Exception as e:
                results[thread_idx] = f"EXCEPTION: {getattr(e, 'code', type(e).__name__)}"
            finally:
                local_db.close()

        t1 = threading.Thread(target=make_request, args=(0,))
        t2 = threading.Thread(target=make_request, args=(1,))
        t1.start()
        t2.start()
        t1.join(timeout=10.0)
        t2.join(timeout=10.0)

        assert not t1.is_alive()
        assert not t2.is_alive()

        assert results.count("SUCCESS") == 1
        assert results.count("CONFLICT") == 1
    finally:
        db_setup.execute(text("DELETE FROM bookings WHERE business_id = :biz_id"), {"biz_id": biz_id})
        db_setup.execute(text("DELETE FROM availability_rules WHERE business_id = :biz_id"), {"biz_id": biz_id})
        db_setup.execute(text("DELETE FROM provider_services WHERE business_id = :biz_id"), {"biz_id": biz_id})
        db_setup.execute(text("DELETE FROM providers WHERE business_id = :biz_id"), {"biz_id": biz_id})
        db_setup.execute(text("DELETE FROM services WHERE business_id = :biz_id"), {"biz_id": biz_id})
        db_setup.execute(text("DELETE FROM admin_users WHERE business_id = :biz_id"), {"biz_id": biz_id})
        db_setup.execute(text("DELETE FROM businesses WHERE id = :biz_id"), {"biz_id": biz_id})
        db_setup.commit()
        db_setup.close()
