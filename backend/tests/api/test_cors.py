def test_cors_headers(client):
    from app.core.config import settings

    response = client.options(
        "/api/public/availability",
        headers={
            "Origin": settings.FRONTEND_URL,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == settings.FRONTEND_URL
    assert response.headers.get("access-control-allow-origin") != "*"


def test_cors_headers_invalid_origin(client):
    response = client.options(
        "/api/public/availability",
        headers={
            "Origin": "http://malicious.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # The server might return 400 or just not include the header
    assert response.headers.get("access-control-allow-origin") != "*"
    assert response.headers.get("access-control-allow-origin") != "http://malicious.com"
