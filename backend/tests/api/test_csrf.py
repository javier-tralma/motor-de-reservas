from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from tests.api.test_admin_auth_api import setup_business_and_admin


def test_csrf_origin_verification_on_mutative_endpoints(client: TestClient, db_session: Session, monkeypatch):
    setup_business_and_admin(db_session, monkeypatch)

    # Missing Origin header on POST login
    res_no_origin = client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
    )
    assert res_no_origin.status_code == 403
    assert res_no_origin.json()["error"]["code"] == "origin_mismatch"

    # Mismatched Origin header on POST login
    res_bad_origin = client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": "https://malicious-site.com"},
    )
    assert res_bad_origin.status_code == 403
    assert res_bad_origin.json()["error"]["code"] == "origin_mismatch"

    # Valid Origin header on POST login
    res_valid = client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_valid.status_code == 200
