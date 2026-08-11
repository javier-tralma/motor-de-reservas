import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.config import settings
from app.core.dependencies import COOKIE_NAME
from app.models.admin_user import AdminUser
from app.models.business import Business


def setup_business_and_admin(db: Session, monkeypatch=None) -> tuple[Business, AdminUser]:
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
    db.refresh(biz)

    admin = AdminUser(
        business_id=biz.id,
        email="admin@estudionomada.cl",
        password_hash=hash_password("Password123!"),
        display_name="Javier",
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return biz, admin


def test_login_success_sets_cookie(client: TestClient, db_session: Session, monkeypatch):
    biz, admin = setup_business_and_admin(db_session, monkeypatch)

    response = client.post(
        "/api/admin/auth/login",
        json={"email": "ADMIN@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["admin"]["id"] == str(admin.id)
    assert data["admin"]["display_name"] == "Javier"
    assert data["admin"]["email"] == "admin@estudionomada.cl"
    assert data["business"]["name"] == "Estudio Nómada"
    assert "token" not in data
    assert "password_hash" not in data
    assert "business_id" not in data["admin"]

    # Cookie attributes
    assert COOKIE_NAME in response.cookies
    cookie = response.cookies.get(COOKIE_NAME)
    assert cookie is not None


def test_login_invalid_credentials_generic(client: TestClient, db_session: Session, monkeypatch):
    setup_business_and_admin(db_session, monkeypatch)

    # Wrong password
    res1 = client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "WrongPassword"},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res1.status_code == 401
    assert res1.json()["error"]["code"] == "invalid_credentials"

    # Nonexistent user
    res2 = client.post(
        "/api/admin/auth/login",
        json={"email": "nobody@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res2.status_code == 401
    assert res2.json()["error"]["code"] == "invalid_credentials"


def test_login_inactive_user_generic_error(client: TestClient, db_session: Session, monkeypatch):
    biz, admin = setup_business_and_admin(db_session, monkeypatch)
    admin.is_active = False
    db_session.commit()

    res = client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "invalid_credentials"


def test_me_endpoint_requires_auth(client: TestClient, db_session: Session, monkeypatch):
    setup_business_and_admin(db_session, monkeypatch)

    # Without cookie
    res = client.get("/api/admin/auth/me")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "session_required"


def test_me_endpoint_with_valid_session(client: TestClient, db_session: Session, monkeypatch):
    setup_business_and_admin(db_session, monkeypatch)

    # Login first
    login_res = client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert login_res.status_code == 200

    # Call /me with cookie
    me_res = client.get("/api/admin/auth/me")
    assert me_res.status_code == 200
    data = me_res.json()["data"]
    assert data["admin"]["email"] == "admin@estudionomada.cl"
    assert data["business"]["name"] == "Estudio Nómada"


def test_logout_revokes_session_and_clears_cookie(client: TestClient, db_session: Session, monkeypatch):
    setup_business_and_admin(db_session, monkeypatch)

    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    logout_res = client.post(
        "/api/admin/auth/logout",
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert logout_res.status_code == 204

    # Check that Set-Cookie instructs the client to delete the cookie
    cookie_header = logout_res.headers.get("set-cookie", "")
    assert COOKIE_NAME in cookie_header
    assert "Path=/api/admin" in cookie_header
    assert "httponly" in cookie_header.lower()
    assert "samesite=lax" in cookie_header.lower()
    assert "max-age=0" in cookie_header.lower() or "expires=" in cookie_header.lower()

    # Subsequent /me should fail
    me_res = client.get("/api/admin/auth/me")
    assert me_res.status_code == 401


def test_login_cookie_attributes_dev_and_prod(client: TestClient, db_session: Session, monkeypatch):
    biz, admin = setup_business_and_admin(db_session, monkeypatch)

    # 1. Development mode
    monkeypatch.setattr(settings, "APP_ENV", "development")
    dev_res = client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert dev_res.status_code == 200
    dev_cookie = dev_res.headers.get("set-cookie", "")
    assert COOKIE_NAME in dev_cookie
    assert "Path=/api/admin" in dev_cookie
    assert "httponly" in dev_cookie.lower()
    assert "samesite=lax" in dev_cookie.lower()
    assert "secure" not in dev_cookie.lower()

    # 2. Production mode
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "SESSION_SECRET", "super-secret-key-for-prod")
    prod_res = client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert prod_res.status_code == 200
    prod_cookie = prod_res.headers.get("set-cookie", "")
    assert "secure" in prod_cookie.lower()


def test_session_business_isolation(client: TestClient, db_session: Session, monkeypatch):
    biz_a, admin_a = setup_business_and_admin(db_session, monkeypatch)

    # Login for Business A
    login_res = client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert login_res.status_code == 200
    token_a = client.cookies.get(COOKIE_NAME)

    # Create Business B
    biz_b_id = uuid.uuid4()
    biz_b = Business(
        id=biz_b_id,
        name="Negocio B",
        slug=f"negocio-b-{uuid.uuid4().hex[:6]}",
        timezone="America/Santiago",
        locale="es-CL",
        email="b@negocio.cl",
    )
    db_session.add(biz_b)
    db_session.commit()

    # Switch configured BUSINESS_ID context to Business B
    monkeypatch.setattr(settings, "BUSINESS_ID", str(biz_b_id))

    # Using token from Business A in Business B context must be rejected (401)
    client.cookies.set(COOKIE_NAME, token_a)
    res = client.get("/api/admin/auth/me")
    assert res.status_code == 401
