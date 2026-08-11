import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.config import settings
from app.models.admin_user import AdminUser
from app.models.booking import Booking, BookingSource, BookingStatus, EmailDeliveryStatus
from app.models.business import Business
from app.models.provider import Provider
from app.models.service import Service


def setup_bookings_test_data(db: Session, monkeypatch=None):
    biz_id = uuid.uuid4()
    if monkeypatch:
        monkeypatch.setattr(settings, "BUSINESS_ID", str(biz_id))
    else:
        settings.BUSINESS_ID = str(biz_id)

    biz = Business(
        id=biz_id,
        name="Estudio Nómada",
        slug=f"estudio-nomada-{uuid.uuid4().hex[:6]}",
        timezone="America/Santiago",
        locale="es-CL",
        email="contacto@estudionomada.cl",
    )
    db.add(biz)
    db.commit()

    admin = AdminUser(
        business_id=biz_id,
        email="admin@estudionomada.cl",
        password_hash=hash_password("Password123!"),
        display_name="Javier",
        is_active=True,
    )
    db.add(admin)

    service = Service(
        id=uuid.uuid4(),
        business_id=biz_id,
        name="Corte de Cabello",
        duration_minutes=30,
        price_amount=15000,
        is_active=True,
    )
    db.add(service)

    provider1 = Provider(
        id=uuid.uuid4(),
        business_id=biz_id,
        name="Camila Rojas",
        is_active=True,
    )
    provider2 = Provider(
        id=uuid.uuid4(),
        business_id=biz_id,
        name="Diego Silva (Retirado)",
        is_active=False,
    )
    db.add_all([provider1, provider2])
    db.commit()

    # Create bookings
    b1 = Booking(
        id=uuid.uuid4(),
        business_id=biz_id,
        service_id=service.id,
        provider_id=provider1.id,
        public_reference="REF_CONFIRMED",
        customer_name="Juan Pérez",
        customer_email="juan@perez.cl",
        customer_phone="+56911111111",
        customer_notes="Nota de cliente 1",
        starts_at=datetime(2026, 8, 10, 14, 0, 0, tzinfo=timezone.utc),  # 10:00 local Santiago
        ends_at=datetime(2026, 8, 10, 14, 30, 0, tzinfo=timezone.utc),
        status=BookingStatus.confirmed,
        source=BookingSource.public,
        service_name_snapshot=service.name,
        duration_minutes_snapshot=30,
        price_amount_snapshot=15000,
        provider_name_snapshot=provider1.name,
        email_delivery_status=EmailDeliveryStatus.not_requested,
    )

    b2 = Booking(
        id=uuid.uuid4(),
        business_id=biz_id,
        service_id=service.id,
        provider_id=provider1.id,
        public_reference="REF_CONFIRMED_2",
        customer_name="María González",
        customer_email="maria@gonzalez.cl",
        customer_phone="+56922222222",
        customer_notes="Nota de cliente 2",
        starts_at=datetime(2026, 8, 10, 15, 0, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 8, 10, 15, 30, 0, tzinfo=timezone.utc),
        status=BookingStatus.confirmed,
        source=BookingSource.public,
        service_name_snapshot=service.name,
        duration_minutes_snapshot=30,
        price_amount_snapshot=15000,
        provider_name_snapshot=provider1.name,
        email_delivery_status=EmailDeliveryStatus.not_requested,
    )

    db.add_all([b1, b2])
    db.commit()

    # Other business data
    other_biz_id = uuid.uuid4()
    other_biz = Business(
        id=other_biz_id,
        name="Otro Negocio",
        slug=f"otro-negocio-{uuid.uuid4().hex[:6]}",
        timezone="America/Santiago",
        locale="es-CL",
        email="otro@negocio.cl",
    )
    db.add(other_biz)
    db.commit()

    other_service = Service(
        id=uuid.uuid4(),
        business_id=other_biz_id,
        name="Servicio Otro",
        duration_minutes=30,
        price_amount=10000,
        is_active=True,
    )
    other_provider = Provider(
        id=uuid.uuid4(),
        business_id=other_biz_id,
        name="Proveedor Otro",
        is_active=True,
    )
    db.add_all([other_service, other_provider])
    db.commit()

    other_booking = Booking(
        id=uuid.uuid4(),
        business_id=other_biz_id,
        service_id=other_service.id,
        provider_id=other_provider.id,
        public_reference="REF_OTHER",
        customer_name="Infiltrado",
        customer_email="infiltrado@test.cl",
        customer_phone="+56999999999",
        customer_notes="Nota infiltrado",
        starts_at=datetime(2026, 8, 10, 14, 0, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 8, 10, 14, 30, 0, tzinfo=timezone.utc),
        status=BookingStatus.confirmed,
        source=BookingSource.public,
        service_name_snapshot=other_service.name,
        duration_minutes_snapshot=30,
        price_amount_snapshot=10000,
        provider_name_snapshot=other_provider.name,
        email_delivery_status=EmailDeliveryStatus.not_requested,
    )
    db.add(other_booking)
    db.commit()

    return biz, admin, service, provider1, provider2, b1, b2, other_biz, other_provider, other_booking


def test_list_admin_bookings_auth_privacy_and_filters(client: TestClient, db_session: Session, monkeypatch):
    biz, admin, service, provider1, provider2, b1, b2, other_biz, other_provider, other_booking = (
        setup_bookings_test_data(db_session, monkeypatch)
    )

    # 1. Without login -> 401
    res_unauth = client.get("/api/admin/bookings")
    assert res_unauth.status_code == 401

    # Login
    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    # 2. List bookings for date 2026-08-10 with filters
    res = client.get(f"/api/admin/bookings?date=2026-08-10&status=confirmed&provider_id={provider1.id}")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 2
    item = data[0]
    assert item["id"] == str(b1.id)
    assert item["customer_name"] == "Juan Pérez"
    assert item["provider_id"] == str(provider1.id)
    assert item["status"] == "confirmed"

    # Confidenciality check: List response MUST NOT contain PII or infra fields
    forbidden_list_fields = [
        "customer_email",
        "customer_phone",
        "customer_notes",
        "business_id",
        "client_request_id",
        "request_fingerprint",
        "email_delivery_status",
        "email_provider_id",
        "email_sent_at",
        "email_last_error_code",
    ]
    for field in forbidden_list_fields:
        assert field not in item, f"Field '{field}' should not be present in list response"

    # 3. Provider from another business -> returns [] without leaking
    res_other_prov = client.get(f"/api/admin/bookings?provider_id={other_provider.id}")
    assert res_other_prov.status_code == 200
    assert res_other_prov.json()["data"] == []


def test_get_admin_booking_detail_and_timezone_offsets(client: TestClient, db_session: Session, monkeypatch):
    biz, admin, service, provider1, provider2, b1, b2, other_biz, other_provider, other_booking = (
        setup_bookings_test_data(db_session, monkeypatch)
    )

    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    # 1. Get detail of own booking -> 200 with PII and IANA timezone offsets
    res = client.get(f"/api/admin/bookings/{b1.id}")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["id"] == str(b1.id)
    assert data["public_reference"] == "REF_CONFIRMED"
    assert data["customer_name"] == "Juan Pérez"
    assert data["customer_email"] == "juan@perez.cl"
    assert data["customer_phone"] == "+56911111111"
    assert data["customer_notes"] == "Nota de cliente 1"

    # Timezone offset check: starts_at, ends_at, created_at, updated_at must include Chile offset (-04:00 or -03:00)
    for tz_field in ["starts_at", "ends_at", "created_at", "updated_at"]:
        val = data[tz_field]
        assert val is not None
        assert "-04:00" in val or "-03:00" in val, f"Field '{tz_field}' must include Chile offset, got '{val}'"

    # Confidentiality check: Detail response MUST NOT contain infra fields
    forbidden_infra_fields = [
        "business_id",
        "client_request_id",
        "request_fingerprint",
        "email_delivery_status",
        "email_provider_id",
        "email_sent_at",
        "email_last_error_code",
    ]
    for field in forbidden_infra_fields:
        assert field not in data, f"Field '{field}' should not be present in detail response"

    # 2. Get detail of other business booking -> 404 booking_not_found
    res_other = client.get(f"/api/admin/bookings/{other_booking.id}")
    assert res_other.status_code == 404
    assert res_other.json()["error"]["code"] == "booking_not_found"

    # 3. Nonexistent UUID -> 404 booking_not_found
    res_fake = client.get(f"/api/admin/bookings/{uuid.uuid4()}")
    assert res_fake.status_code == 404
    assert res_fake.json()["error"]["code"] == "booking_not_found"


def test_update_admin_booking_status_cancelled_and_no_show(client: TestClient, db_session: Session, monkeypatch):
    biz, admin, service, provider1, provider2, b1, b2, other_biz, other_provider, other_booking = (
        setup_bookings_test_data(db_session, monkeypatch)
    )

    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    # 1. Transition b1 -> cancelled
    res_cancel = client.patch(
        f"/api/admin/bookings/{b1.id}/status",
        json={"status": "cancelled"},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_cancel.status_code == 200
    data_cancel = res_cancel.json()["data"]
    assert data_cancel["status"] == "cancelled"
    assert data_cancel["cancelled_at"] is not None
    assert "-04:00" in data_cancel["cancelled_at"] or "-03:00" in data_cancel["cancelled_at"]

    # 2. Transition b2 -> no_show
    res_noshow = client.patch(
        f"/api/admin/bookings/{b2.id}/status",
        json={"status": "no_show"},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_noshow.status_code == 200
    data_noshow = res_noshow.json()["data"]
    assert data_noshow["status"] == "no_show"
    assert data_noshow["no_show_at"] is not None
    assert "-04:00" in data_noshow["no_show_at"] or "-03:00" in data_noshow["no_show_at"]


def test_update_admin_booking_status_validations_and_422_envelope(client: TestClient, db_session: Session, monkeypatch):
    biz, admin, service, provider1, provider2, b1, b2, other_biz, other_provider, other_booking = (
        setup_bookings_test_data(db_session, monkeypatch)
    )

    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    # 1. Missing Origin header -> 403
    res_no_origin = client.patch(
        f"/api/admin/bookings/{b1.id}/status",
        json={"status": "completed"},
    )
    assert res_no_origin.status_code == 403

    # 2. Invalid status in body ("confirmed" or arbitrary) -> 422 with standard error envelope
    res_invalid_status = client.patch(
        f"/api/admin/bookings/{b1.id}/status",
        json={"status": "arbitrary_invalid_status"},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_invalid_status.status_code == 422
    err_body = res_invalid_status.json()
    assert "error" in err_body
    assert err_body["error"]["code"] == "validation_error"
    assert "message" in err_body["error"]
    assert "request_id" in err_body["error"]
    assert "details" in err_body["error"]

    # 3. Extra parameter in body -> 422 (extra="forbid")
    res_extra_param = client.patch(
        f"/api/admin/bookings/{b1.id}/status",
        json={"status": "completed", "extra_field": "hacked"},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_extra_param.status_code == 422

    # 4. Booking from another business -> 404
    res_other_biz = client.patch(
        f"/api/admin/bookings/{other_booking.id}/status",
        json={"status": "completed"},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_other_biz.status_code == 404

    # 5. Valid transition: confirmed -> completed
    res_complete = client.patch(
        f"/api/admin/bookings/{b1.id}/status",
        json={"status": "completed"},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_complete.status_code == 200
    data_complete = res_complete.json()["data"]
    assert data_complete["status"] == "completed"
    assert data_complete["completed_at"] is not None
    assert "-04:00" in data_complete["completed_at"] or "-03:00" in data_complete["completed_at"]

    # 6. Subsequent transition from terminal state (completed -> cancelled) -> 409
    res_terminal = client.patch(
        f"/api/admin/bookings/{b1.id}/status",
        json={"status": "cancelled"},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_terminal.status_code == 409
    assert res_terminal.json()["error"]["code"] == "invalid_status_transition"


def test_get_admin_providers_returns_active_and_inactive(client: TestClient, db_session: Session, monkeypatch):
    biz, admin, service, provider1, provider2, b1, b2, other_biz, other_provider, other_booking = (
        setup_bookings_test_data(db_session, monkeypatch)
    )

    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    res = client.get("/api/admin/providers")
    assert res.status_code == 200
    providers = res.json()["data"]
    assert len(providers) == 2
    names = [p["name"] for p in providers]
    assert "Camila Rojas" in names
    assert "Diego Silva (Retirado)" in names
