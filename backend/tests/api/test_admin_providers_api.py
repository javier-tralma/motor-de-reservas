import threading
import uuid
from datetime import datetime, time, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.auth import hash_password
from app.core.config import settings
from app.models.admin_user import AdminUser
from app.models.availability import AvailabilityRule
from app.models.business import Business
from app.models.provider import Provider, ProviderService
from app.models.service import Service
from app.services.catalog_service import CatalogService
from tests.conftest import engine as db_engine


def setup_providers_test_data(db: Session, monkeypatch=None):
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
        phone="+56912345678",
        bio="Especialista en corte",
        is_active=True,
        sort_order=0,
    )
    db.add(p1)

    s1 = Service(
        id=uuid.uuid4(),
        business_id=biz_id,
        name="Corte de Cabello",
        description="Corte clásico",
        duration_minutes=30,
        price_amount=15000,
        is_active=True,
        sort_order=0,
    )
    s2 = Service(
        id=uuid.uuid4(),
        business_id=biz_id,
        name="Peinado",
        description="Peinado evento",
        duration_minutes=45,
        price_amount=20000,
        is_active=True,
        sort_order=1,
    )
    db.add_all([s1, s2])
    db.commit()

    # Link p1 to s1
    ps1 = ProviderService(business_id=biz_id, provider_id=p1.id, service_id=s1.id)
    db.add(ps1)

    rule1 = AvailabilityRule(
        id=uuid.uuid4(),
        business_id=biz_id,
        provider_id=p1.id,
        weekday=0,  # Monday
        start_time=time(9, 0),
        end_time=time(18, 0),
    )
    db.add(rule1)
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

    other_provider = Provider(
        id=uuid.uuid4(),
        business_id=other_biz_id,
        name="Proveedor Otro",
        is_active=True,
    )
    other_service = Service(
        id=uuid.uuid4(),
        business_id=other_biz_id,
        name="Servicio Otro",
        duration_minutes=30,
        price_amount=10000,
        is_active=True,
    )
    db.add_all([other_provider, other_service])
    db.commit()

    return biz, admin, p1, s1, s2, other_biz, other_provider, other_service


def test_admin_providers_list_and_detail_minimal_vs_full(client: TestClient, db_session: Session, monkeypatch):
    biz, admin, p1, s1, s2, other_biz, other_provider, other_service = setup_providers_test_data(
        db_session, monkeypatch
    )

    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    # 1. GET /api/admin/providers -> Minimal list ({id, name, is_active})
    res_list = client.get("/api/admin/providers")
    assert res_list.status_code == 200
    providers = res_list.json()["data"]
    assert len(providers) == 1
    item = providers[0]
    assert item["id"] == str(p1.id)
    assert item["name"] == "Camila Rojas"
    assert item["is_active"] is True
    assert "email" not in item
    assert "phone" not in item
    assert "bio" not in item

    # 2. GET /api/admin/providers/{id} -> Full detail
    res_detail = client.get(f"/api/admin/providers/{p1.id}")
    assert res_detail.status_code == 200
    detail = res_detail.json()["data"]
    assert detail["id"] == str(p1.id)
    assert detail["name"] == "Camila Rojas"
    assert detail["email"] == "camila@estudionomada.cl"
    assert detail["phone"] == "+56912345678"
    assert detail["bio"] == "Especialista en corte"

    # 3. GET provider of another business -> 404
    res_other = client.get(f"/api/admin/providers/{other_provider.id}")
    assert res_other.status_code == 404
    assert res_other.json()["error"]["code"] == "provider_not_found"


def test_admin_providers_create_update_and_phone_validations(client: TestClient, db_session: Session, monkeypatch):
    biz, admin, p1, s1, s2, other_biz, other_provider, other_service = setup_providers_test_data(
        db_session, monkeypatch
    )

    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    # 1. Invalid phone format ("abc", "+569 abc", "12345") -> 422
    for bad_phone in ["abc", "+569 abc", "12345"]:
        res_bad_phone = client.post(
            "/api/admin/providers",
            json={"name": "Nuevo Prov", "phone": bad_phone},
            headers={"Origin": settings.FRONTEND_URL},
        )
        assert res_bad_phone.status_code == 422, f"Phone '{bad_phone}' should fail validation"

    # 2. Valid phone format ("+56987654321", "+56 9 1234 5678") and empty string normalization to null -> 201
    res_valid_phone = client.post(
        "/api/admin/providers",
        json={"name": "Gonzalo Valenzuela", "phone": " +56 9 1234 5678 ", "bio": " Barbero "},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_valid_phone.status_code == 201
    p_data = res_valid_phone.json()["data"]
    assert p_data["name"] == "Gonzalo Valenzuela"
    assert p_data["phone"] == "+56 9 1234 5678"
    assert p_data["bio"] == "Barbero"

    # Empty string phone normalizes to None/null
    res_empty_phone = client.post(
        "/api/admin/providers",
        json={"name": "Sin Telefono", "phone": "   "},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_empty_phone.status_code == 201
    assert res_empty_phone.json()["data"]["phone"] is None

    # 3. PATCH clearing email/phone with null -> 200
    res_clear = client.patch(
        f"/api/admin/providers/{p1.id}",
        json={"email": None, "phone": None},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_clear.status_code == 200
    cleared_data = res_clear.json()["data"]
    assert cleared_data["email"] is None
    assert cleared_data["phone"] is None

    # 4. PATCH with empty body -> 422
    res_empty_patch = client.patch(
        f"/api/admin/providers/{p1.id}",
        json={},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_empty_patch.status_code == 422


def test_admin_provider_services_assignment(client: TestClient, db_session: Session, monkeypatch):
    biz, admin, p1, s1, s2, other_biz, other_provider, other_service = setup_providers_test_data(
        db_session, monkeypatch
    )

    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    # 1. GET /api/admin/providers/{id}/services -> initial [s1.id]
    res_get_services = client.get(f"/api/admin/providers/{p1.id}/services")
    assert res_get_services.status_code == 200
    assert res_get_services.json()["data"]["service_ids"] == [str(s1.id)]

    # 2. Duplicate service_ids in PUT request -> 422
    res_dup = client.put(
        f"/api/admin/providers/{p1.id}/services",
        json={"service_ids": [str(s1.id), str(s1.id)]},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_dup.status_code == 422
    assert res_dup.json()["error"]["code"] == "validation_error"

    # 3. Assign service of another business -> 404 without altering DB
    res_other_svc = client.put(
        f"/api/admin/providers/{p1.id}/services",
        json={"service_ids": [str(other_service.id)]},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_other_svc.status_code == 404
    assert res_other_svc.json()["error"]["code"] == "service_not_found"

    # Verify original DB state unchanged
    db_services = db_session.query(ProviderService.service_id).filter_by(business_id=biz.id, provider_id=p1.id).all()
    assert len(db_services) == 1
    assert db_services[0][0] == s1.id

    # 4. Valid replacement with [s1.id, s2.id] -> 200
    res_replace = client.put(
        f"/api/admin/providers/{p1.id}/services",
        json={"service_ids": [str(s1.id), str(s2.id)]},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_replace.status_code == 200
    assert set(res_replace.json()["data"]["service_ids"]) == {str(s1.id), str(s2.id)}

    # 5. Replacement with empty list [] -> 200
    res_empty = client.put(
        f"/api/admin/providers/{p1.id}/services",
        json={"service_ids": []},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_empty.status_code == 200
    assert res_empty.json()["data"]["service_ids"] == []


def test_concurrent_provider_services_replacement_with_barrier():
    SessionMaker = sessionmaker(bind=db_engine)
    setup_session = SessionMaker()

    biz_id = None
    other_biz_id = None
    p1_id = None
    s1_id = None
    s2_id = None

    original_business_id = getattr(settings, "BUSINESS_ID", None)

    try:
        biz, admin, p1, s1, s2, other_biz, other_provider, other_service = setup_providers_test_data(setup_session)
        biz_id = biz.id
        other_biz_id = other_biz.id
        p1_id = p1.id
        s1_id = s1.id
        s2_id = s2.id

        barrier = threading.Barrier(2, timeout=5.0)
        results = [None, None]
        exceptions = [None, None]

        payload_a = [s1_id]
        payload_b = [s2_id]

        def worker(thread_idx, service_ids):
            session = SessionMaker()
            try:
                catalog_svc = CatalogService(session)

                # Wait at barrier immediately BEFORE attempting to call service / obtain FOR UPDATE lock
                barrier.wait()

                res = catalog_svc.replace_provider_services(
                    business_id=biz_id,
                    provider_id=p1_id,
                    service_ids=service_ids,
                )
                results[thread_idx] = res
            except Exception as e:
                exceptions[thread_idx] = e
            finally:
                session.close()

        t1 = threading.Thread(target=worker, args=(0, payload_a))
        t2 = threading.Thread(target=worker, args=(1, payload_b))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Both valid operations return success
        assert exceptions[0] is None, f"Thread 0 failed with {exceptions[0]}"
        assert exceptions[1] is None, f"Thread 1 failed with {exceptions[1]}"
        assert results[0] is not None
        assert results[1] is not None

        # Verify final DB state is EXACTLY equal to payload_a or payload_b (never union, intersection or duplicates)
        verify_session = SessionMaker()
        try:
            db_assigned = (
                verify_session.query(ProviderService.service_id).filter_by(business_id=biz_id, provider_id=p1_id).all()
            )
            final_ids = [r[0] for r in db_assigned]
            assert (final_ids == payload_a) or (final_ids == payload_b), (
                f"Final DB state must be exactly Payload A or Payload B, got {final_ids}"
            )
        finally:
            verify_session.close()

    finally:
        setattr(settings, "BUSINESS_ID", original_business_id)

        if biz_id or other_biz_id:
            cleanup_session = SessionMaker()
            try:
                biz_ids = [bid for bid in (biz_id, other_biz_id) if bid]
                cleanup_session.query(ProviderService).filter(ProviderService.business_id.in_(biz_ids)).delete()
                cleanup_session.query(AvailabilityRule).filter(AvailabilityRule.business_id.in_(biz_ids)).delete()
                cleanup_session.query(Provider).filter(Provider.business_id.in_(biz_ids)).delete()
                cleanup_session.query(Service).filter(Service.business_id.in_(biz_ids)).delete()
                cleanup_session.query(AdminUser).filter(AdminUser.business_id.in_(biz_ids)).delete()
                cleanup_session.query(Business).filter(Business.id.in_(biz_ids)).delete()
                cleanup_session.commit()
            except Exception:
                cleanup_session.rollback()
            finally:
                cleanup_session.close()
        setup_session.close()


def test_inactive_service_or_provider_excluded_from_public_availability(
    client: TestClient, db_session: Session, monkeypatch
):
    from app.api.endpoints.availability import get_availability_service
    from app.domain.availability import AvailabilityEngine
    from app.services.availability_service import AvailabilityService

    biz, admin, p1, s1, s2, other_biz, other_provider, other_service = setup_providers_test_data(
        db_session, monkeypatch
    )

    def mock_now(tz="UTC"):
        return datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)

    def override_get_availability_service():
        return AvailabilityService(db_session, engine=AvailabilityEngine(get_now_fn=mock_now))

    client.app.dependency_overrides[get_availability_service] = override_get_availability_service

    try:
        # Date Monday 2026-08-10
        target_date = "2026-08-10"

        # Initially, active service s1 with active provider p1 has available slots
        res_active = client.get(f"/api/public/availability?service_id={s1.id}&date={target_date}")
        assert res_active.status_code == 200
        slots_active = res_active.json()["data"]["slots"]
        assert len(slots_active) > 0

        # 1. Soft-deactivate service s1 -> Public availability returns 404
        s1.is_active = False
        db_session.commit()

        res_inactive_svc = client.get(f"/api/public/availability?service_id={s1.id}&date={target_date}")
        assert res_inactive_svc.status_code == 404

        # Restore service s1, deactivate provider p1
        s1.is_active = True
        p1.is_active = False
        db_session.commit()

        res_inactive_prov = client.get(f"/api/public/availability?service_id={s1.id}&date={target_date}")
        assert res_inactive_prov.status_code == 200
        slots_inactive_prov = res_inactive_prov.json()["data"]["slots"]
        # Deactivated provider is excluded, so 0 slots available
        assert len(slots_inactive_prov) == 0
    finally:
        client.app.dependency_overrides.clear()


def test_admin_providers_null_rejected_for_non_nullable_fields(client: TestClient, db_session: Session, monkeypatch):
    biz, admin, p1, s1, s2, other_biz, other_provider, other_service = setup_providers_test_data(
        db_session, monkeypatch
    )

    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    for field in ["name", "bio", "is_active", "sort_order"]:
        res_null = client.patch(
            f"/api/admin/providers/{p1.id}",
            json={field: None},
            headers={"Origin": settings.FRONTEND_URL},
        )
        assert res_null.status_code == 422

    # Verify email and phone can be null
    res_null_allowed = client.patch(
        f"/api/admin/providers/{p1.id}",
        json={"email": None, "phone": None},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_null_allowed.status_code == 200


def test_admin_providers_timestamps_are_in_business_timezone(client: TestClient, db_session: Session, monkeypatch):
    from datetime import datetime, timedelta, timezone

    biz, admin, p1, s1, s2, other_biz, other_provider, other_service = setup_providers_test_data(
        db_session, monkeypatch
    )

    # Set explicit known UTC timestamps on p1
    # July is winter (offset -04:00 in America/Santiago)
    # January is summer (offset -03:00 in America/Santiago)
    known_created_utc = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    known_updated_utc = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

    p1.created_at = known_created_utc
    p1.updated_at = known_updated_utc
    db_session.commit()

    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    res = client.get(f"/api/admin/providers/{p1.id}")
    assert res.status_code == 200
    provider_data = res.json()["data"]

    created_at_str = provider_data["created_at"]
    updated_at_str = provider_data["updated_at"]

    # 1. Assert exact ISO 8601 strings with America/Santiago local offsets
    assert created_at_str == "2026-07-15T08:00:00-04:00"
    assert updated_at_str == "2026-01-15T09:00:00-03:00"

    # 2. Parse and verify tzinfo & exact offset values
    created_dt = datetime.fromisoformat(created_at_str)
    updated_dt = datetime.fromisoformat(updated_at_str)

    assert created_dt.utcoffset() == timedelta(hours=-4)
    assert updated_dt.utcoffset() == timedelta(hours=-3)
    assert created_at_str.endswith("-04:00")
    assert updated_at_str.endswith("-03:00")
    assert not created_at_str.endswith("+00:00")
    assert not created_at_str.endswith("Z")
