import uuid
from datetime import datetime, timezone

from app.core.config import settings
from app.models.booking import Booking, BookingSource, BookingStatus, EmailDeliveryStatus
from app.models.business import Business
from app.models.provider import Provider, ProviderService
from app.models.service import Service


def test_get_public_business(client, db_session, monkeypatch):
    b_id = uuid.uuid4()
    monkeypatch.setattr(settings, "BUSINESS_ID", b_id)

    business = Business(
        id=b_id,
        name="Estudio Nómada",
        slug="estudio-nomada-test",
        timezone="America/Santiago",
        locale="es-CL",
        currency="CLP",
        email="hola@estudionomada.cl",
        phone="+56912345678",
        address="Calle Valparaíso 123",
        booking_horizon_days=60,
    )
    db_session.add(business)
    db_session.commit()

    response = client.get("/api/public/business")
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["name"] == "Estudio Nómada"
    assert data["slug"] == "estudio-nomada-test"
    assert data["timezone"] == "America/Santiago"
    assert data["email"] == "hola@estudionomada.cl"
    assert data["phone"] == "+56912345678"
    assert data["address"] == "Calle Valparaíso 123"

    # Verificar que no expone business_id, created_at, etc.
    assert "id" not in data
    assert "business_id" not in data
    assert "created_at" not in data


def test_get_public_services_and_isolation(client, db_session, monkeypatch):
    b_id = uuid.uuid4()
    b_other_id = uuid.uuid4()
    monkeypatch.setattr(settings, "BUSINESS_ID", b_id)

    b1 = Business(id=b_id, name="B1", slug=f"b1-{uuid.uuid4().hex[:6]}", email="b1@b.com")
    b2 = Business(id=b_other_id, name="B2", slug=f"b2-{uuid.uuid4().hex[:6]}", email="b2@b.com")
    db_session.add_all([b1, b2])

    s1 = Service(
        id=uuid.uuid4(),
        business_id=b_id,
        name="Corte",
        duration_minutes=30,
        price_amount=10000,
        is_active=True,
        sort_order=2,
    )
    s2 = Service(
        id=uuid.uuid4(),
        business_id=b_id,
        name="Barba",
        duration_minutes=20,
        price_amount=8000,
        is_active=True,
        sort_order=1,
    )
    s_inactive = Service(
        id=uuid.uuid4(),
        business_id=b_id,
        name="Inactivo",
        duration_minutes=10,
        price_amount=5000,
        is_active=False,
        sort_order=0,
    )
    s_other = Service(
        id=uuid.uuid4(),
        business_id=b_other_id,
        name="Otro Negocio",
        duration_minutes=15,
        price_amount=3000,
        is_active=True,
        sort_order=0,
    )

    db_session.add_all([s1, s2, s_inactive, s_other])
    db_session.commit()

    response = client.get("/api/public/services")
    assert response.status_code == 200
    data = response.json()["data"]

    # Solamente activos del negocio b_id, ordenados por sort_order
    assert len(data) == 2
    assert data[0]["name"] == "Barba"
    assert data[1]["name"] == "Corte"


def test_get_public_service_providers(client, db_session, monkeypatch):
    b_id = uuid.uuid4()
    b_other_id = uuid.uuid4()
    monkeypatch.setattr(settings, "BUSINESS_ID", b_id)

    b1 = Business(id=b_id, name="B1", slug=f"b1-{uuid.uuid4().hex[:6]}", email="b1@b.com")
    b2 = Business(id=b_other_id, name="B2", slug=f"b2-{uuid.uuid4().hex[:6]}", email="b2@b.com")
    db_session.add_all([b1, b2])

    s_id = uuid.uuid4()
    service = Service(id=s_id, business_id=b_id, name="Corte", duration_minutes=30, price_amount=10000, is_active=True)

    p1 = Provider(id=uuid.uuid4(), business_id=b_id, name="Camila", bio="Bio C", is_active=True, sort_order=1)
    p2 = Provider(id=uuid.uuid4(), business_id=b_id, name="Javier", bio="Bio J", is_active=True, sort_order=2)
    p_inactive = Provider(id=uuid.uuid4(), business_id=b_id, name="Pedro", bio="Bio P", is_active=False, sort_order=0)

    ps1 = ProviderService(business_id=b_id, provider_id=p1.id, service_id=s_id)
    ps2 = ProviderService(business_id=b_id, provider_id=p2.id, service_id=s_id)
    ps_inact = ProviderService(business_id=b_id, provider_id=p_inactive.id, service_id=s_id)

    db_session.add_all([service, p1, p2, p_inactive, ps1, ps2, ps_inact])
    db_session.commit()

    response = client.get(f"/api/public/services/{s_id}/providers")
    assert response.status_code == 200
    data = response.json()["data"]

    assert len(data) == 2
    assert data[0]["name"] == "Camila"
    assert data[1]["name"] == "Javier"
    assert "email" not in data[0]


def test_get_booking_confirmation(client, db_session, monkeypatch):
    b_id = uuid.uuid4()
    monkeypatch.setattr(settings, "BUSINESS_ID", b_id)

    business = Business(
        id=b_id,
        name="Estudio Nómada",
        slug=f"estudio-nomada-{uuid.uuid4().hex[:6]}",
        email="hola@estudionomada.cl",
        phone="+56912345678",
        address="Calle Valparaíso 123",
    )
    s_id = uuid.uuid4()
    p_id = uuid.uuid4()
    service = Service(id=s_id, business_id=b_id, name="Corte", duration_minutes=45, price_amount=15000)
    provider = Provider(id=p_id, business_id=b_id, name="Camila")
    ps = ProviderService(business_id=b_id, provider_id=p_id, service_id=s_id)
    db_session.add_all([business, service, provider, ps])
    db_session.flush()

    ref = "ref123456789"
    starts_at = datetime(2026, 8, 12, 14, 0, tzinfo=timezone.utc)
    ends_at = datetime(2026, 8, 12, 14, 45, tzinfo=timezone.utc)

    booking = Booking(
        business_id=b_id,
        service_id=s_id,
        provider_id=p_id,
        public_reference=ref,
        client_request_id=uuid.uuid4(),
        request_fingerprint="fingerprint",
        customer_name="Juan Perez",
        customer_email="juan.perez@example.com",
        customer_phone="+56900000000",
        customer_notes="Mis notas",
        starts_at=starts_at,
        ends_at=ends_at,
        status=BookingStatus.confirmed,
        source=BookingSource.public,
        service_name_snapshot="Corte de Cabello",
        duration_minutes_snapshot=45,
        price_amount_snapshot=15000,
        provider_name_snapshot="Camila Rojas",
        email_delivery_status=EmailDeliveryStatus.sent,
    )
    db_session.add(booking)
    db_session.commit()

    response = client.get(f"/api/public/bookings/{ref}/confirmation")
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["public_reference"] == ref
    assert data["status"] == "confirmed"
    assert data["service"]["name"] == "Corte de Cabello"
    assert data["provider"]["name"] == "Camila Rojas"
    assert data["customer_email_masked"] == "j********z@example.com"
    assert data["business"]["name"] == "Estudio Nómada"
    assert data["business"]["address"] == "Calle Valparaíso 123"

    # Verificar que NO expone IDs internos, notas, teléfono o datos sensibles
    assert "id" not in data
    assert "business_id" not in data
    assert "customer_name" not in data
    assert "customer_phone" not in data
    assert "customer_notes" not in data


def test_cross_tenant_isolation_and_404(client, db_session, monkeypatch):
    b_id = uuid.uuid4()
    b_other_id = uuid.uuid4()
    monkeypatch.setattr(settings, "BUSINESS_ID", b_id)

    b1 = Business(id=b_id, name="B1", slug=f"b1-{uuid.uuid4().hex[:6]}", email="b1@b.com")
    b2 = Business(id=b_other_id, name="B2", slug=f"b2-{uuid.uuid4().hex[:6]}", email="b2@b.com")
    db_session.add_all([b1, b2])

    # Servicio inactivo en b1
    s_inactive = Service(
        id=uuid.uuid4(), business_id=b_id, name="Inactivo", duration_minutes=30, price_amount=10000, is_active=False
    )

    # Servicio y profesional en b2 (otro negocio real)
    s_other = Service(
        id=uuid.uuid4(), business_id=b_other_id, name="Otro", duration_minutes=30, price_amount=10000, is_active=True
    )
    p_other = Provider(id=uuid.uuid4(), business_id=b_other_id, name="Otro Prov", is_active=True)
    ps_other = ProviderService(business_id=b_other_id, provider_id=p_other.id, service_id=s_other.id)

    db_session.add_all([s_inactive, s_other, p_other, ps_other])
    db_session.flush()

    # Reserva en b2 (otro negocio real)
    ref_other = "ref-other-biz-123"
    b_other = Booking(
        business_id=b_other_id,
        service_id=s_other.id,
        provider_id=p_other.id,
        public_reference=ref_other,
        client_request_id=uuid.uuid4(),
        request_fingerprint="fp_other",
        customer_name="Otro Cliente",
        customer_email="other@example.com",
        customer_phone="+56933333333",
        starts_at=datetime(2026, 8, 12, 14, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 8, 12, 14, 45, tzinfo=timezone.utc),
        status=BookingStatus.confirmed,
        source=BookingSource.public,
        service_name_snapshot="Otro",
        duration_minutes_snapshot=30,
        price_amount_snapshot=10000,
        provider_name_snapshot="Otro Prov",
        email_delivery_status=EmailDeliveryStatus.sent,
    )
    db_session.add(b_other)
    db_session.commit()

    # 1. Servicio inactivo devuelve 404 en providers
    resp_inact = client.get(f"/api/public/services/{s_inactive.id}/providers")
    assert resp_inact.status_code == 404

    # 2. Servicio de otro negocio devuelve 404 en providers
    resp_other_s = client.get(f"/api/public/services/{s_other.id}/providers")
    assert resp_other_s.status_code == 404

    # 3. Confirmación de reserva de otro negocio devuelve 404
    resp_other_b = client.get(f"/api/public/bookings/{ref_other}/confirmation")
    assert resp_other_b.status_code == 404


def test_confirmation_timestamps_timezone_offset(client, db_session, monkeypatch):
    b_id = uuid.uuid4()
    monkeypatch.setattr(settings, "BUSINESS_ID", b_id)

    business = Business(
        id=b_id,
        name="Estudio Nómada",
        slug=f"nomada-{uuid.uuid4().hex[:6]}",
        timezone="America/Santiago",
        email="hola@estudionomada.cl",
    )
    s_id = uuid.uuid4()
    p_id = uuid.uuid4()
    service = Service(id=s_id, business_id=b_id, name="Corte", duration_minutes=45, price_amount=15000)
    provider = Provider(id=p_id, business_id=b_id, name="Camila")
    ps = ProviderService(business_id=b_id, provider_id=p_id, service_id=s_id)

    db_session.add_all([business, service, provider, ps])
    db_session.flush()

    # Reserva en Invierno (15 Julio: UTC-4 -> offset -04:00 en Santiago)
    starts_winter = datetime(2026, 7, 15, 14, 0, tzinfo=timezone.utc)
    ends_winter = datetime(2026, 7, 15, 14, 45, tzinfo=timezone.utc)
    b_winter = Booking(
        business_id=b_id,
        service_id=s_id,
        provider_id=p_id,
        public_reference="ref-winter-123",
        client_request_id=uuid.uuid4(),
        request_fingerprint="fp_winter",
        customer_name="Test Winter",
        customer_email="winter@example.com",
        customer_phone="+56911111111",
        starts_at=starts_winter,
        ends_at=ends_winter,
        status=BookingStatus.confirmed,
        source=BookingSource.public,
        service_name_snapshot="Corte",
        duration_minutes_snapshot=45,
        price_amount_snapshot=15000,
        provider_name_snapshot="Camila",
        email_delivery_status=EmailDeliveryStatus.sent,
    )

    # Reserva en Verano (15 Enero: UTC-3 -> offset -03:00 en Santiago)
    starts_summer = datetime(2026, 1, 15, 13, 0, tzinfo=timezone.utc)
    ends_summer = datetime(2026, 1, 15, 13, 45, tzinfo=timezone.utc)
    b_summer = Booking(
        business_id=b_id,
        service_id=s_id,
        provider_id=p_id,
        public_reference="ref-summer-123",
        client_request_id=uuid.uuid4(),
        request_fingerprint="fp_summer",
        customer_name="Test Summer",
        customer_email="summer@example.com",
        customer_phone="+56922222222",
        starts_at=starts_summer,
        ends_at=ends_summer,
        status=BookingStatus.confirmed,
        source=BookingSource.public,
        service_name_snapshot="Corte",
        duration_minutes_snapshot=45,
        price_amount_snapshot=15000,
        provider_name_snapshot="Camila",
        email_delivery_status=EmailDeliveryStatus.sent,
    )

    db_session.add_all([b_winter, b_summer])
    db_session.commit()

    resp_w = client.get("/api/public/bookings/ref-winter-123/confirmation")
    assert resp_w.status_code == 200
    data_w = resp_w.json()["data"]
    assert "-04:00" in data_w["starts_at"]

    resp_s = client.get("/api/public/bookings/ref-summer-123/confirmation")
    assert resp_s.status_code == 200
    data_s = resp_s.json()["data"]
    assert "-03:00" in data_s["starts_at"]
