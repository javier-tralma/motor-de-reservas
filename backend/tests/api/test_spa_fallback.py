from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_system_health_endpoints(client: TestClient):
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json() == {"status": "ok"}

    res_live = client.get("/health/live")
    assert res_live.status_code == 200
    assert res_live.json() == {"status": "ok"}

    res_ready = client.get("/health/ready")
    assert res_ready.status_code == 200
    assert res_ready.json() == {"status": "ok"}


def test_openapi_and_docs_endpoints(client: TestClient):
    res_openapi = client.get("/openapi.json")
    assert res_openapi.status_code == 200
    assert "openapi" in res_openapi.json()

    res_docs = client.get("/docs")
    assert res_docs.status_code == 200
    assert "Swagger UI" in res_docs.text or "swagger-ui" in res_docs.text


def test_unmatched_api_routes_return_404_not_html(client: TestClient):
    res = client.get("/api/unknown_endpoint_404")
    assert res.status_code == 404
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "not_found"


def test_mutative_method_on_spa_route_is_not_served_as_html(client: TestClient):
    res = client.post("/admin/dashboard")
    assert res.status_code in (404, 405)


def test_spa_fallback_when_dist_directory_exists(client: TestClient, tmp_path: Path):
    # Setup temporary dist folder
    mock_dist = tmp_path / "frontend_dist"
    mock_dist.mkdir()
    assets_dir = mock_dist / "assets"
    assets_dir.mkdir()

    index_html = mock_dist / "index.html"
    index_html.write_text("<!DOCTYPE html><html><body><div id='root'>Vite App</div></body></html>", encoding="utf-8")

    sample_css = assets_dir / "index-abc123.css"
    sample_css.write_text("body { background: #000; }", encoding="utf-8")

    favicon = mock_dist / "favicon.ico"
    favicon.write_bytes(b"dummy-favicon-bytes")

    with patch("app.main.FRONTEND_DIST_DIR", mock_dist):
        # 1. Root route
        res_root = client.get("/")
        assert res_root.status_code == 200
        assert "Vite App" in res_root.text

        # 2. React direct route refresh
        res_admin = client.get("/admin/dashboard")
        assert res_admin.status_code == 200
        assert "Vite App" in res_admin.text

        # 3. Deep React route refresh
        res_deep = client.get("/reservar/confirmacion/DEMO-REF-001")
        assert res_deep.status_code == 200
        assert "Vite App" in res_deep.text

        # 4. Existing static asset
        res_asset = client.get("/assets/index-abc123.css")
        assert res_asset.status_code == 200
        assert "background: #000;" in res_asset.text

        # 5. Non-existent asset must return 404, NOT index.html
        res_missing_asset = client.get("/assets/missing-file.js")
        assert res_missing_asset.status_code == 404
        assert "Vite App" not in res_missing_asset.text

        # 6. Root-level static file (favicon)
        res_fav = client.get("/favicon.ico")
        assert res_fav.status_code == 200
        assert res_fav.content == b"dummy-favicon-bytes"


def test_spa_fallback_when_dist_does_not_exist(client: TestClient, tmp_path: Path):
    non_existent_dist = tmp_path / "non_existent"

    with patch("app.main.FRONTEND_DIST_DIR", non_existent_dist):
        res = client.get("/admin/dashboard")
        assert res.status_code == 404
        assert "error" in res.json()
