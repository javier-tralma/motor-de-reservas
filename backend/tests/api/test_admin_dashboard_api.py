import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.config import settings
from app.core.dependencies import get_utc_now
from app.main import app
from app.models.admin_user import AdminUser
from app.models.booking import Booking, BookingSource, BookingStatus, EmailDeliveryStatus
from app.models.business import Business
from app.models.provider import Provider
from app.models.service import Service


def setup_dashboard_test_data(db: Session, monkeypatch=None):
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

    provider = Provider(
        id=uuid.uuid4(),
        business_id=biz_id,
        name="Camila Rojas",
        is_active=True,
    )
    db.add(provider)

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
    db.add(other_service)
    other_provider = Provider(
        id=uuid.uuid4(),
        business_id=other_biz_id,
        name="Proveedor Otro",
        is_active=True,
    )
    db.add(other_provider)
    db.commit()

    return biz, admin, service, provider, other_biz, other_service, other_provider


def test_dashboard_requires_auth(client: TestClient, db_session: Session, monkeypatch):
    setup_dashboard_test_data(db_session, monkeypatch)
    res = client.get("/api/admin/dashboard")
    assert res.status_code == 401


def test_dashboard_empty_agenda(client: TestClient, db_session: Session, monkeypatch):
    setup_dashboard_test_data(db_session, monkeypatch)

    # Login
    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    res = client.get("/api/admin/dashboard")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["timezone"] == "America/Santiago"
    assert data["summary"]["total"] == 0
    assert data["summary"]["confirmed_remaining"] == 0
    assert data["summary"]["completed"] == 0
    assert data["summary"]["cancelled"] == 0
    assert data["summary"]["no_show"] == 0
    assert data["next_booking"] is None
    assert data["agenda"] == []


def test_dashboard_with_bookings_and_timezone_boundary(client: TestClient, db_session: Session, monkeypatch):
    (
        biz,
        admin,
        service,
        provider,
        other_biz,
        other_service,
        other_provider,
    ) = setup_dashboard_test_data(db_session, monkeypatch)

    # Test date in local Santiago time: 2026-08-10 14:00:00 (which is 2026-08-10 18:00:00 UTC during UTC-4)
    # 2026-08-10 in America/Santiago (UTC-4):
    # Day bounds in UTC: 2026-08-10 04:00:00 UTC to 2026-08-11 04:00:00 UTC

    now_test_utc = datetime(2026, 8, 10, 16, 0, 0, tzinfo=timezone.utc)  # 12:00 local Santiago

    # Booking 1: Earlier today local (10:00 local = 14:00 UTC), status=completed
    b1 = Booking(
        id=uuid.uuid4(),
        business_id=biz.id,
        service_id=service.id,
        provider_id=provider.id,
        public_reference="REF1",
        customer_name="Juan Pérez",
        customer_email="juan@perez.cl",
        customer_phone="+56911111111",
        customer_notes="Nota secreta de cliente",
        starts_at=datetime(2026, 8, 10, 14, 0, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 8, 10, 14, 30, 0, tzinfo=timezone.utc),
        status=BookingStatus.completed,
        source=BookingSource.public,
        service_name_snapshot=service.name,
        duration_minutes_snapshot=30,
        price_amount_snapshot=15000,
        provider_name_snapshot=provider.name,
        email_delivery_status=EmailDeliveryStatus.not_requested,
    )

    # Booking 2: Later today local (15:00 local = 19:00 UTC), status=confirmed (future relative to 12:00 local)
    b2 = Booking(
        id=uuid.uuid4(),
        business_id=biz.id,
        service_id=service.id,
        provider_id=provider.id,
        public_reference="REF2",
        customer_name="Maria Gomez",
        customer_email="maria@gomez.cl",
        customer_phone="+56922222222",
        customer_notes="Otra nota",
        starts_at=datetime(2026, 8, 10, 19, 0, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 8, 10, 19, 30, 0, tzinfo=timezone.utc),
        status=BookingStatus.confirmed,
        source=BookingSource.public,
        service_name_snapshot=service.name,
        duration_minutes_snapshot=30,
        price_amount_snapshot=15000,
        provider_name_snapshot=provider.name,
        email_delivery_status=EmailDeliveryStatus.not_requested,
    )

    # Booking 3: Cancelled today
    b3 = Booking(
        id=uuid.uuid4(),
        business_id=biz.id,
        service_id=service.id,
        provider_id=provider.id,
        public_reference="REF3",
        customer_name="Pedro Soto",
        customer_email="pedro@soto.cl",
        customer_phone="+56933333333",
        customer_notes="Cancelada",
        starts_at=datetime(2026, 8, 10, 20, 0, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 8, 10, 20, 30, 0, tzinfo=timezone.utc),
        status=BookingStatus.cancelled,
        source=BookingSource.public,
        service_name_snapshot=service.name,
        duration_minutes_snapshot=30,
        price_amount_snapshot=15000,
        provider_name_snapshot=provider.name,
        email_delivery_status=EmailDeliveryStatus.not_requested,
    )

    # Booking 4: Other business booking (should NOT appear)
    b_other = Booking(
        id=uuid.uuid4(),
        business_id=other_biz.id,
        service_id=other_service.id,
        provider_id=other_provider.id,
        public_reference="REF_OTHER",
        customer_name="Infiltrado",
        customer_email="infiltrado@test.cl",
        customer_phone="+56999999999",
        customer_notes="Nota infiltrado",
        starts_at=datetime(2026, 8, 10, 19, 0, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 8, 10, 19, 30, 0, tzinfo=timezone.utc),
        status=BookingStatus.confirmed,
        source=BookingSource.public,
        service_name_snapshot=other_service.name,
        duration_minutes_snapshot=30,
        price_amount_snapshot=10000,
        provider_name_snapshot=other_provider.name,
        email_delivery_status=EmailDeliveryStatus.not_requested,
    )

    db_session.add_all([b1, b2, b3, b_other])
    db_session.commit()

    # Login
    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    app.dependency_overrides[get_utc_now] = lambda: now_test_utc

    try:
        res = client.get("/api/admin/dashboard")
    finally:
        app.dependency_overrides.pop(get_utc_now, None)

    assert res.status_code == 200

    data = res.json()["data"]
    assert data["date"] == "2026-08-10"
    summary = data["summary"]
    assert summary["total"] == 3
    assert summary["completed"] == 1
    assert summary["confirmed_remaining"] == 1
    assert summary["cancelled"] == 1
    assert summary["no_show"] == 0

    # Next booking check
    next_booking = data["next_booking"]
    assert next_booking is not None
    assert next_booking["customer_name"] == "Maria Gomez"

    # Agenda order check
    agenda = data["agenda"]
    assert len(agenda) == 3
    assert agenda[0]["customer_name"] == "Juan Pérez"
    assert agenda[1]["customer_name"] == "Maria Gomez"
    assert agenda[2]["customer_name"] == "Pedro Soto"

    # Confidentiality check: NO customer_email, customer_phone, customer_notes in payload
    for item in agenda:
        assert "customer_email" not in item
        assert "customer_phone" not in item
        assert "customer_notes" not in item


def test_dashboard_ignores_now_query_string_and_uses_injected_clock(
    client: TestClient, db_session: Session, monkeypatch
):
    setup_dashboard_test_data(db_session, monkeypatch)

    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    injected_now = datetime(2026, 8, 10, 16, 0, 0, tzinfo=timezone.utc)
    app.dependency_overrides[get_utc_now] = lambda: injected_now

    try:
        # Pass a completely different date via ?now= query param
        res = client.get("/api/admin/dashboard?now=1999-01-01T00:00:00Z")
    finally:
        app.dependency_overrides.pop(get_utc_now, None)

    assert res.status_code == 200
    data = res.json()["data"]
    # Should reflect injected date 2026-08-10, NOT 1999-01-01
    assert data["date"] == "2026-08-10"
