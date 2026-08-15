import json
import logging
import uuid
from datetime import datetime, timezone

import httpx
import pytest

from app.integrations.email.resend import RESEND_API_URL, ResendEmailService
from app.integrations.email.service import BookingEmailData, EmailDeliveryStatus


@pytest.fixture
def sample_booking():
    return BookingEmailData(
        booking_id=uuid.uuid4(),
        public_reference="REF123456",
        customer_name="Valeria Soto",
        customer_email="valeria@example.com",
        starts_at=datetime(2026, 8, 12, 14, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 8, 12, 14, 45, tzinfo=timezone.utc),
        duration_minutes=45,
        service_name="Consulta General",
        provider_name="Dra. Valenzuela",
        business_name="Estudio Nómada",
        business_timezone="America/Santiago",
        business_address="Av. Providencia 123",
        business_phone="+56911223344",
    )


def test_resend_email_service_validation():
    with pytest.raises(ValueError, match="api_key must not be empty"):
        ResendEmailService(api_key="", from_email="reservas@test.cl")

    with pytest.raises(ValueError, match="from_email must not be empty"):
        ResendEmailService(api_key="re_123", from_email="")


def test_resend_email_service_success(sample_booking, caplog):
    caplog.set_level(logging.INFO)

    def handle_request(request: httpx.Request) -> httpx.Response:
        assert request.url == RESEND_API_URL
        assert request.headers["Authorization"] == "Bearer re_test_key_123"
        assert request.headers["Content-Type"] == "application/json"

        body = json.loads(request.content.decode("utf-8"))
        assert body["from"] == "Estudio Nómada <reservas@test.cl>"
        assert body["to"] == ["valeria@example.com"]
        assert body["subject"] == "Confirmación de reserva en Estudio Nómada"
        assert "Valeria Soto" in body["html"]
        assert "Valeria Soto" in body["text"]
        assert "Dra. Valenzuela" in body["html"]

        return httpx.Response(200, json={"id": "resend_msg_abc123"})

    client = httpx.Client(transport=httpx.MockTransport(handle_request))
    service = ResendEmailService(
        api_key="re_test_key_123",
        from_email="Estudio Nómada <reservas@test.cl>",
        client=client,
    )

    result = service.send_booking_confirmation(sample_booking)

    assert result.status == EmailDeliveryStatus.sent
    assert result.provider_id == "resend_msg_abc123"
    assert result.error_code is None

    # Check logs: email is masked, API key is NOT logged
    assert "re_test_key_123" not in caplog.text
    assert "valeria@example.com" not in caplog.text
    assert "v*****a@example.com" in caplog.text


def test_resend_email_service_api_error_does_not_leak_pii_from_resend_response(sample_booking, caplog):
    caplog.set_level(logging.WARNING)

    # Response contains sensitive customer email and phone in message
    def handle_request(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={
                "statusCode": 422,
                "name": "validation_error",
                "message": "Recipient valeria@secret.com or phone +56999999999 rejected by upstream",
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handle_request))
    service = ResendEmailService(
        api_key="re_test_key_123",
        from_email="reservas@test.cl",
        client=client,
    )

    result = service.send_booking_confirmation(sample_booking)

    assert result.status == EmailDeliveryStatus.failed
    assert result.provider_id is None
    # Code is normalized and contains NO external strings
    assert result.error_code == "resend_http_4xx"

    # Verify that external PII in message was NOT logged
    assert "valeria@secret.com" not in caplog.text
    assert "+56999999999" not in caplog.text
    assert "validation_error" not in caplog.text


def test_resend_email_service_500_error(sample_booking, caplog):
    caplog.set_level(logging.WARNING)

    def handle_request(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, content=b"Internal Server Error")

    client = httpx.Client(transport=httpx.MockTransport(handle_request))
    service = ResendEmailService(
        api_key="re_test_key_123",
        from_email="reservas@test.cl",
        client=client,
    )

    result = service.send_booking_confirmation(sample_booking)

    assert result.status == EmailDeliveryStatus.failed
    assert result.error_code == "resend_http_5xx"


def test_resend_email_service_missing_id_in_200_response(sample_booking, caplog):
    caplog.set_level(logging.WARNING)

    def handle_request(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    client = httpx.Client(transport=httpx.MockTransport(handle_request))
    service = ResendEmailService(
        api_key="re_test_key_123",
        from_email="reservas@test.cl",
        client=client,
    )

    result = service.send_booking_confirmation(sample_booking)

    assert result.status == EmailDeliveryStatus.failed
    assert result.error_code == "resend_invalid_response"


def test_resend_email_service_timeout(sample_booking, caplog):
    caplog.set_level(logging.ERROR)

    def handle_request(_request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("Connection timed out")

    client = httpx.Client(transport=httpx.MockTransport(handle_request))
    service = ResendEmailService(
        api_key="re_test_key_123",
        from_email="reservas@test.cl",
        client=client,
    )

    result = service.send_booking_confirmation(sample_booking)

    assert result.status == EmailDeliveryStatus.failed
    assert result.provider_id is None
    assert result.error_code == "resend_timeout"


def test_resend_email_service_network_exception(sample_booking, caplog):
    caplog.set_level(logging.ERROR)

    def handle_request(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    client = httpx.Client(transport=httpx.MockTransport(handle_request))
    service = ResendEmailService(
        api_key="re_test_key_123",
        from_email="reservas@test.cl",
        client=client,
    )

    result = service.send_booking_confirmation(sample_booking)

    assert result.status == EmailDeliveryStatus.failed
    assert result.provider_id is None
    assert result.error_code == "resend_network_error"
