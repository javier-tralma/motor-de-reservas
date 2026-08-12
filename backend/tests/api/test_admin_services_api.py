import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.config import settings
from app.models.admin_user import AdminUser
from app.models.business import Business
from app.models.service import Service


def setup_services_test_data(db: Session, monkeypatch=None):
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
    db.add(s1)
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
        description="Otro",
        duration_minutes=30,
        price_amount=10000,
        is_active=True,
        sort_order=0,
    )
    db.add(other_service)
    db.commit()

    return biz, admin, s1, other_biz, other_service


def test_admin_services_auth_and_csrf(client: TestClient, db_session: Session, monkeypatch):
    biz, admin, s1, other_biz, other_service = setup_services_test_data(db_session, monkeypatch)

    # 1. Unauthenticated -> 401
    res_unauth = client.get("/api/admin/services")
    assert res_unauth.status_code == 401

    # Login
    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    # 2. POST without Origin header -> 403
    res_no_origin = client.post(
        "/api/admin/services",
        json={
            "name": "Barba",
            "description": "Perfilado",
            "duration_minutes": 20,
            "price_amount": 8000,
        },
    )
    assert res_no_origin.status_code == 403


def test_admin_services_crud_and_validations(client: TestClient, db_session: Session, monkeypatch):
    biz, admin, s1, other_biz, other_service = setup_services_test_data(db_session, monkeypatch)

    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    # 1. GET /api/admin/services -> 200
    res_list = client.get("/api/admin/services")
    assert res_list.status_code == 200
    services = res_list.json()["data"]
    assert len(services) == 1
    assert services[0]["id"] == str(s1.id)
    assert services[0]["name"] == "Corte de Cabello"

    # 2. POST /api/admin/services -> 201
    res_create = client.post(
        "/api/admin/services",
        json={
            "name": " Coloración Capilar ",
            "description": "Tinte completo ",
            "duration_minutes": 90,
            "price_amount": 45000,
            "is_active": True,
            "sort_order": 1,
        },
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_create.status_code == 201
    created_data = res_create.json()["data"]
    assert created_data["name"] == "Coloración Capilar"  # trimmed
    assert created_data["description"] == "Tinte completo"  # trimmed
    assert created_data["duration_minutes"] == 90
    assert created_data["price_amount"] == 45000

    # 3. Invalid validations -> 422
    # Invalid duration (< 5)
    res_inv_dur = client.post(
        "/api/admin/services",
        json={
            "name": "Test",
            "duration_minutes": 2,
            "price_amount": 1000,
        },
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_inv_dur.status_code == 422

    # Extra parameter -> 422 (extra="forbid")
    res_extra = client.post(
        "/api/admin/services",
        json={
            "name": "Test",
            "duration_minutes": 30,
            "price_amount": 1000,
            "extra_param": "invalid",
        },
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_extra.status_code == 422

    # 4. PATCH /api/admin/services/{id} -> 200
    # Update is_active to False and sort_order to 0
    res_patch = client.patch(
        f"/api/admin/services/{s1.id}",
        json={
            "is_active": False,
            "sort_order": 0,
        },
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_patch.status_code == 200
    updated_data = res_patch.json()["data"]
    assert updated_data["is_active"] is False
    assert updated_data["sort_order"] == 0

    # Verify soft deactivation preserves record in DB
    db_service = db_session.query(Service).filter_by(id=s1.id).scalar()
    assert db_service is not None
    assert db_service.is_active is False

    # 5. PATCH with empty body -> 422
    res_empty_patch = client.patch(
        f"/api/admin/services/{s1.id}",
        json={},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_empty_patch.status_code == 422

    # 6. Service of another business -> 404
    res_other = client.patch(
        f"/api/admin/services/{other_service.id}",
        json={"name": "Hacked"},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_other.status_code == 404
    assert res_other.json()["error"]["code"] == "service_not_found"


def test_admin_services_null_rejected_for_non_nullable_fields(client: TestClient, db_session: Session, monkeypatch):
    biz, admin, s1, other_biz, other_service = setup_services_test_data(db_session, monkeypatch)

    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    for field in ["name", "duration_minutes", "price_amount", "is_active", "sort_order", "description"]:
        res_null = client.patch(
            f"/api/admin/services/{s1.id}",
            json={field: None},
            headers={"Origin": settings.FRONTEND_URL},
        )
        assert res_null.status_code == 422

    # Verify falsy values still work
    res_falsy = client.patch(
        f"/api/admin/services/{s1.id}",
        json={"is_active": False, "sort_order": 0, "description": ""},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_falsy.status_code == 200


def test_admin_services_timestamps_are_in_business_timezone(client: TestClient, db_session: Session, monkeypatch):
    from datetime import datetime, timedelta, timezone

    biz, admin, s1, other_biz, other_service = setup_services_test_data(db_session, monkeypatch)

    # Set explicit known UTC timestamps on s1
    # July is winter (offset -04:00 in America/Santiago)
    # January is summer (offset -03:00 in America/Santiago)
    known_created_utc = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    known_updated_utc = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

    s1.created_at = known_created_utc
    s1.updated_at = known_updated_utc
    db_session.commit()

    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    res = client.get("/api/admin/services")
    assert res.status_code == 200
    services = res.json()["data"]
    target_service = next(s for s in services if s["id"] == str(s1.id))

    created_at_str = target_service["created_at"]
    updated_at_str = target_service["updated_at"]

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
