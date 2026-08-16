from fastapi.testclient import TestClient

from app.main import FRONTEND_DIST_DIR, app

client = TestClient(app)


def test_real_frontend_dist_same_origin_serving():
    assert FRONTEND_DIST_DIR.is_dir(), "frontend/dist must be built before this test runs"

    # 1. System Health & Docs
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json() == {"status": "ok"}

    res_docs = client.get("/docs")
    assert res_docs.status_code == 200

    res_openapi = client.get("/openapi.json")
    assert res_openapi.status_code == 200
    assert "openapi" in res_openapi.json()

    # 2. Public API endpoint
    res_services = client.get("/api/public/services")
    assert res_services.status_code == 200
    assert "data" in res_services.json()

    # 3. SPA root
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "text/html" in res_root.headers.get("content-type", "")
    assert '<div id="root">' in res_root.text

    # 4. Direct refresh on React routes
    res_admin = client.get("/admin/dashboard")
    assert res_admin.status_code == 200
    assert '<div id="root">' in res_admin.text

    res_booking = client.get("/reservar")
    assert res_booking.status_code == 200
    assert '<div id="root">' in res_booking.text

    # 5. Real compiled assets
    assets = list((FRONTEND_DIST_DIR / "assets").glob("*.js"))
    assert len(assets) > 0
    real_asset_name = assets[0].name

    res_asset = client.get(f"/assets/{real_asset_name}")
    assert res_asset.status_code == 200
    assert len(res_asset.content) > 0

    # 6. Non-existent asset must 404 (never return SPA index.html)
    res_missing_asset = client.get("/assets/definitely-not-found-asset.js")
    assert res_missing_asset.status_code == 404
    assert '<div id="root">' not in res_missing_asset.text

    # 7. Unmatched API endpoint must return API error envelope (never SPA index.html)
    res_missing_api = client.get("/api/public/nonexistent_route")
    assert res_missing_api.status_code == 404
    data = res_missing_api.json()
    assert "error" in data
