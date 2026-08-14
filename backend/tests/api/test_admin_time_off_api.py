import uuid
from datetime import datetime, time, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.config import settings
from app.models.admin_user import AdminUser
from app.models.availability import AvailabilityRule, TimeOff
from app.models.booking import Booking, BookingSource, BookingStatus, EmailDeliveryStatus
from app.models.business import Business
from app.models.provider import Provider, ProviderService
from app.models.service import Service


def setup_time_off_test_data(db: Session, monkeypatch=None):
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

    p1 = Provider(
        id=uuid.uuid4(),
        business_id=biz_id,
        name="Camila Rojas",
        email="camila@estudionomada.cl",
        is_active=True,
        sort_order=0,
    )
    p_inactive = Provider(
        id=uuid.uuid4(),
        business_id=biz_id,
        name="Gonzalo Inactivo",
        email="gonzalo@estudionomada.cl",
        is_active=False,
        sort_order=1,
    )
    db.add_all([p1, p_inactive])

    s1 = Service(
        id=uuid.uuid4(),
        business_id=biz_id,
        name="Corte Clásico",
        description="Corte de cabello",
        duration_minutes=30,
        price_amount=15000,
        is_active=True,
        sort_order=0,
    )
    db.add(s1)
    db.commit()

    ps1 = ProviderService(business_id=biz_id, provider_id=p1.id, service_id=s1.id)
    db.add(ps1)

    # Monday availability rule for p1 (09:00 - 18:00)
    rule1 = AvailabilityRule(
        id=uuid.uuid4(),
        business_id=biz_id,
        provider_id=p1.id,
        weekday=0,
        start_time=time(9, 0),
        end_time=time(18, 0),
    )
    db.add(rule1)
    db.commit()

    # Other business
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

    other_provider = Provider(
        id=uuid.uuid4(),
        business_id=other_biz_id,
        name="Proveedor Otro",
        is_active=True,
    )
    db.add(other_provider)
    db.commit()

    other_to = TimeOff(
        id=uuid.uuid4(),
        business_id=other_biz_id,
        provider_id=other_provider.id,
        starts_at=datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 8, 15, 18, 0, tzinfo=timezone.utc),
        reason="Bloqueo ajeno",
    )
    db.add(other_to)
    db.commit()

    return biz, admin, p1, p_inactive, s1, other_biz, other_provider, other_to


def test_admin_time_off_auth_csrf_and_query_validation(client: TestClient, db_session: Session, monkeypatch):
    biz, admin, p1, p_inactive, s1, other_biz, other_provider, other_to = setup_time_off_test_data(
        db_session, monkeypatch
    )

    # 1. Unauthenticated GET -> 401
    res_unauth_get = client.get(f"/api/admin/time-off?provider_id={p1.id}")
    assert res_unauth_get.status_code == 401

    # 2. Unauthenticated POST -> 401
    res_unauth_post = client.post(
        "/api/admin/time-off",
        json={
            "provider_id": str(p1.id),
            "starts_at_local": "2026-08-15T09:00:00",
            "ends_at_local": "2026-08-15T18:00:00",
        },
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_unauth_post.status_code == 401

    # 3. Unauthenticated DELETE -> 401
    res_unauth_del = client.delete(f"/api/admin/time-off/{uuid.uuid4()}")
    assert res_unauth_del.status_code == 401

    # Login
    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    # 4. GET without mandatory provider_id query param -> 422
    res_missing_param = client.get("/api/admin/time-off")
    assert res_missing_param.status_code == 422

    # 5. POST without Origin -> 403
    res_no_origin = client.post(
        "/api/admin/time-off",
        json={
            "provider_id": str(p1.id),
            "starts_at_local": "2026-08-15T09:00:00",
            "ends_at_local": "2026-08-15T18:00:00",
        },
    )
    assert res_no_origin.status_code == 403

    # 6. DELETE without Origin -> 403
    res_del_no_origin = client.delete(f"/api/admin/time-off/{uuid.uuid4()}")
    assert res_del_no_origin.status_code == 403


def test_admin_time_off_get_active_and_past_filtering(client: TestClient, db_session: Session, monkeypatch):
    from app.api.admin.time_off import get_availability_admin_service
    from app.services.availability_admin_service import AvailabilityAdminService

    biz, admin, p1, p_inactive, s1, other_biz, other_provider, other_to = setup_time_off_test_data(
        db_session, monkeypatch
    )

    # Current reference time: 2026-08-15 12:00:00 UTC
    ref_now = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Past block (ended before ref_now)
    past_to = TimeOff(
        id=uuid.uuid4(),
        business_id=biz.id,
        provider_id=p1.id,
        starts_at=datetime(2026, 8, 10, 9, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 8, 10, 18, 0, tzinfo=timezone.utc),
        reason="Bloqueo pasado",
    )
    # 2. Active / future block 1 (starts today, ends tomorrow)
    active_to_1 = TimeOff(
        id=uuid.uuid4(),
        business_id=biz.id,
        provider_id=p1.id,
        starts_at=datetime(2026, 8, 15, 9, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 8, 16, 18, 0, tzinfo=timezone.utc),
        reason="Bloqueo actual",
    )
    # 3. Future block 2 (starts next week)
    future_to_2 = TimeOff(
        id=uuid.uuid4(),
        business_id=biz.id,
        provider_id=p1.id,
        starts_at=datetime(2026, 8, 20, 9, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 8, 25, 18, 0, tzinfo=timezone.utc),
        reason="Vacaciones futuras",
    )
    db_session.add_all([past_to, active_to_1, future_to_2])
    db_session.commit()

    def override_get_service():
        return AvailabilityAdminService(db_session, get_now_fn=lambda tz="UTC": ref_now)

    client.app.dependency_overrides[get_availability_admin_service] = override_get_service

    try:
        client.post(
            "/api/admin/auth/login",
            json={"email": "admin@estudionomada.cl", "password": "Password123!"},
            headers={"Origin": settings.FRONTEND_URL},
        )

        res = client.get(f"/api/admin/time-off?provider_id={p1.id}")
        assert res.status_code == 200
        items = res.json()["data"]

        # Only 2 blocks returned (past block is excluded because ends_at <= ref_now)
        assert len(items) == 2
        assert items[0]["id"] == str(active_to_1.id)
        assert items[1]["id"] == str(future_to_2.id)

        # Cross-tenant provider -> 404
        res_other = client.get(f"/api/admin/time-off?provider_id={other_provider.id}")
        assert res_other.status_code == 404
        assert res_other.json()["error"]["code"] == "provider_not_found"
    finally:
        client.app.dependency_overrides.clear()


def test_admin_time_off_create_validations_and_dst(client: TestClient, db_session: Session, monkeypatch):
    biz, admin, p1, p_inactive, s1, other_biz, other_provider, other_to = setup_time_off_test_data(
        db_session, monkeypatch
    )

    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    # 1. Reject explicit offset or 'Z' in starts_at_local or ends_at_local -> 422
    for bad_input in [
        {"starts_at_local": "2026-08-15T09:00:00-04:00", "ends_at_local": "2026-08-15T18:00:00"},
        {"starts_at_local": "2026-08-15T09:00:00Z", "ends_at_local": "2026-08-15T18:00:00"},
        {"starts_at_local": "2026-08-15T09:00:00+00:00", "ends_at_local": "2026-08-15T18:00:00"},
        {"starts_at_local": "2026-08-15T09:00:00", "ends_at_local": "2026-08-15T18:00:00-04:00"},
    ]:
        res_bad_offset = client.post(
            "/api/admin/time-off",
            json={"provider_id": str(p1.id), "reason": "Test", **bad_input},
            headers={"Origin": settings.FRONTEND_URL},
        )
        assert res_bad_offset.status_code == 422, f"Payload {bad_input} with offset/Z must be rejected with 422"

    # 2. Reject starts_at_local >= ends_at_local -> 422 invalid_time_range
    res_range = client.post(
        "/api/admin/time-off",
        json={
            "provider_id": str(p1.id),
            "starts_at_local": "2026-08-15T18:00:00",
            "ends_at_local": "2026-08-15T09:00:00",
            "reason": "Test",
        },
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_range.status_code == 422
    assert res_range.json()["error"]["code"] == "invalid_time_range"

    # 3. Normalization of reason (whitespace or empty -> null)
    res_whitespace = client.post(
        "/api/admin/time-off",
        json={
            "provider_id": str(p1.id),
            "starts_at_local": "2026-08-15T09:00:00",
            "ends_at_local": "2026-08-15T18:00:00",
            "reason": "    ",
        },
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_whitespace.status_code == 201
    assert res_whitespace.json()["data"]["reason"] is None

    res_trimmed = client.post(
        "/api/admin/time-off",
        json={
            "provider_id": str(p1.id),
            "starts_at_local": "2026-08-16T09:00:00",
            "ends_at_local": "2026-08-16T18:00:00",
            "reason": "   Vacaciones de invierno   ",
        },
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_trimmed.status_code == 201
    assert res_trimmed.json()["data"]["reason"] == "Vacaciones de invierno"

    # 4. Reason > 240 chars -> 422
    res_long_reason = client.post(
        "/api/admin/time-off",
        json={
            "provider_id": str(p1.id),
            "starts_at_local": "2026-08-17T09:00:00",
            "ends_at_local": "2026-08-17T18:00:00",
            "reason": "x" * 241,
        },
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_long_reason.status_code == 422

    # 5. Inactive provider can have time_off -> 201
    res_inactive = client.post(
        "/api/admin/time-off",
        json={
            "provider_id": str(p_inactive.id),
            "starts_at_local": "2026-08-18T09:00:00",
            "ends_at_local": "2026-08-18T18:00:00",
            "reason": "Permiso",
        },
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_inactive.status_code == 201
    assert res_inactive.json()["data"]["provider_id"] == str(p_inactive.id)

    # 6. Provider from another business -> 404
    res_other_p = client.post(
        "/api/admin/time-off",
        json={
            "provider_id": str(other_provider.id),
            "starts_at_local": "2026-08-19T09:00:00",
            "ends_at_local": "2026-08-19T18:00:00",
        },
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_other_p.status_code == 404
    assert res_other_p.json()["error"]["code"] == "provider_not_found"

    # 7. Exact offsets for Chile:
    # Winter date (July): offset -04:00
    res_winter = client.post(
        "/api/admin/time-off",
        json={
            "provider_id": str(p1.id),
            "starts_at_local": "2026-07-20T09:00:00",
            "ends_at_local": "2026-07-20T18:00:00",
            "reason": "Invierno",
        },
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_winter.status_code == 201
    winter_data = res_winter.json()["data"]
    assert winter_data["starts_at"] == "2026-07-20T09:00:00-04:00"
    assert winter_data["ends_at"] == "2026-07-20T18:00:00-04:00"

    # Summer date (January): offset -03:00
    res_summer = client.post(
        "/api/admin/time-off",
        json={
            "provider_id": str(p1.id),
            "starts_at_local": "2026-01-20T09:00:00",
            "ends_at_local": "2026-01-20T18:00:00",
            "reason": "Verano",
        },
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_summer.status_code == 201
    summer_data = res_summer.json()["data"]
    assert summer_data["starts_at"] == "2026-01-20T09:00:00-03:00"
    assert summer_data["ends_at"] == "2026-01-20T18:00:00-03:00"

    # 8. Non-existent time during DST jump in Chile (e.g. 2026-09-06 at 00:30:00) -> 422 non_existent_local_time
    # In Chile, at midnight of the first Sunday of September (2026-09-06 00:00), clocks jump to 01:00.
    # Therefore 2026-09-06 00:30:00 is a non-existent local time.
    res_dst_gap = client.post(
        "/api/admin/time-off",
        json={
            "provider_id": str(p1.id),
            "starts_at_local": "2026-09-06T00:30:00",
            "ends_at_local": "2026-09-06T04:00:00",
            "reason": "Salto DST",
        },
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_dst_gap.status_code == 422
    assert res_dst_gap.json()["error"]["code"] == "non_existent_local_time"


def test_admin_time_off_delete_and_scoping(client: TestClient, db_session: Session, monkeypatch):
    biz, admin, p1, p_inactive, s1, other_biz, other_provider, other_to = setup_time_off_test_data(
        db_session, monkeypatch
    )

    to = TimeOff(
        id=uuid.uuid4(),
        business_id=biz.id,
        provider_id=p1.id,
        starts_at=datetime(2026, 8, 15, 9, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 8, 15, 18, 0, tzinfo=timezone.utc),
        reason="A eliminar",
    )
    db_session.add(to)
    db_session.commit()

    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    # 1. DELETE cross-tenant time off -> 404
    res_other_del = client.delete(f"/api/admin/time-off/{other_to.id}", headers={"Origin": settings.FRONTEND_URL})
    assert res_other_del.status_code == 404
    assert res_other_del.json()["error"]["code"] == "time_off_not_found"

    # 2. DELETE non-existent time off -> 404
    res_non_existent = client.delete(f"/api/admin/time-off/{uuid.uuid4()}", headers={"Origin": settings.FRONTEND_URL})
    assert res_non_existent.status_code == 404
    assert res_non_existent.json()["error"]["code"] == "time_off_not_found"

    # 3. DELETE existing time off -> 204 No Content
    res_del = client.delete(f"/api/admin/time-off/{to.id}", headers={"Origin": settings.FRONTEND_URL})
    assert res_del.status_code == 204
    assert res_del.text == ""

    # Verify deleted from DB
    deleted = db_session.query(TimeOff).filter_by(id=to.id).first()
    assert deleted is None


def test_time_off_public_availability_regression_and_booking_invariance(
    client: TestClient, db_session: Session, monkeypatch
):
    from app.api.endpoints.availability import get_availability_service
    from app.domain.availability import AvailabilityEngine
    from app.services.availability_service import AvailabilityService

    biz, admin, p1, p_inactive, s1, other_biz, other_provider, other_to = setup_time_off_test_data(
        db_session, monkeypatch
    )

    # Target date is Monday 2026-08-10 (provider p1 works 09:00 - 18:00)
    target_date = "2026-08-10"

    # Create pre-existing confirmed booking on Monday at 14:00 - 14:30
    booking_start = datetime(2026, 8, 10, 18, 0, 0, tzinfo=timezone.utc)  # 14:00 in America/Santiago (-04:00)
    booking_end = datetime(2026, 8, 10, 18, 30, 0, tzinfo=timezone.utc)  # 14:30 in America/Santiago (-04:00)

    existing_booking = Booking(
        id=uuid.uuid4(),
        business_id=biz.id,
        service_id=s1.id,
        provider_id=p1.id,
        public_reference="REF12345",
        customer_name="Juan Perez",
        customer_email="juan@perez.cl",
        customer_phone="+56911223344",
        customer_notes="",
        starts_at=booking_start,
        ends_at=booking_end,
        status=BookingStatus.confirmed,
        source=BookingSource.public,
        service_name_snapshot="Corte Clásico",
        duration_minutes_snapshot=30,
        price_amount_snapshot=15000,
        provider_name_snapshot="Camila Rojas",
        email_delivery_status=EmailDeliveryStatus.sent,
    )
    db_session.add(existing_booking)
    db_session.commit()

    def mock_now(tz="UTC"):
        return datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)

    def override_get_availability_service():
        return AvailabilityService(db_session, engine=AvailabilityEngine(get_now_fn=mock_now))

    client.app.dependency_overrides[get_availability_service] = override_get_availability_service

    try:
        # 1. Check initial public availability before time_off
        res_initial = client.get(f"/api/public/availability?service_id={s1.id}&date={target_date}")
        assert res_initial.status_code == 200
        initial_slots = res_initial.json()["data"]["slots"]
        assert len(initial_slots) > 0

        # Slot at 10:00 (14:00 UTC) is initially available
        slot_10_00_found = any("10:00:00" in s["starts_at"] for s in initial_slots)
        assert slot_10_00_found is True

        # 2. Login as admin and create time_off covering 09:00 to 12:00
        client.post(
            "/api/admin/auth/login",
            json={"email": "admin@estudionomada.cl", "password": "Password123!"},
            headers={"Origin": settings.FRONTEND_URL},
        )

        res_create_to = client.post(
            "/api/admin/time-off",
            json={
                "provider_id": str(p1.id),
                "starts_at_local": "2026-08-10T09:00:00",
                "ends_at_local": "2026-08-10T12:00:00",
                "reason": "Capacitacion matutina",
            },
            headers={"Origin": settings.FRONTEND_URL},
        )
        assert res_create_to.status_code == 201
        created_to_id = res_create_to.json()["data"]["id"]

        # 3. Check public availability -> Slots between 09:00 and 12:00 are now excluded
        res_blocked = client.get(f"/api/public/availability?service_id={s1.id}&date={target_date}")
        assert res_blocked.status_code == 200
        blocked_slots = res_blocked.json()["data"]["slots"]

        # Verify no slots between 09:00 and 12:00 exist
        assert not any(
            "09:00:00" in s["starts_at"] or "10:00:00" in s["starts_at"] or "11:30:00" in s["starts_at"]
            for s in blocked_slots
        )
        # Afternoon slots (e.g. 15:00) are still available
        assert any("15:00:00" in s["starts_at"] for s in blocked_slots)

        # 4. Invariance: Existing booking at 14:00 remains confirmed and untouched
        booking_in_db = db_session.query(Booking).filter_by(id=existing_booking.id).one()
        assert booking_in_db.status == BookingStatus.confirmed
        assert booking_in_db.starts_at == booking_start
        assert booking_in_db.ends_at == booking_end

        # 5. Delete time_off -> Slots between 09:00 and 12:00 are restored
        res_del = client.delete(f"/api/admin/time-off/{created_to_id}", headers={"Origin": settings.FRONTEND_URL})
        assert res_del.status_code == 204

        res_restored = client.get(f"/api/public/availability?service_id={s1.id}&date={target_date}")
        assert res_restored.status_code == 200
        restored_slots = res_restored.json()["data"]["slots"]
        assert any("10:00:00" in s["starts_at"] for s in restored_slots)
        assert len(restored_slots) == len(initial_slots)

    finally:
        client.app.dependency_overrides.clear()
