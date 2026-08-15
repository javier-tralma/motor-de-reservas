import uuid
from datetime import datetime, timezone

from app.integrations.email.service import BookingEmailData
from app.integrations.email.templates import (
    format_spanish_date,
    render_booking_confirmation_html,
    render_booking_confirmation_subject,
    render_booking_confirmation_text,
)


def test_format_spanish_date():
    # 2026-08-12 is a Wednesday (miércoles)
    dt = datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc)
    formatted = format_spanish_date(dt)
    assert formatted == "miércoles, 12 de agosto de 2026"


def test_render_templates_with_timezone_shift():
    # 2026-08-11 02:00:00 UTC is 2026-08-10 22:00:00 in America/Santiago (UTC-4)
    starts_utc = datetime(2026, 8, 11, 2, 0, tzinfo=timezone.utc)
    ends_utc = datetime(2026, 8, 11, 2, 45, tzinfo=timezone.utc)

    booking = BookingEmailData(
        booking_id=uuid.uuid4(),
        public_reference="REF123456",
        customer_name="Valeria Soto",
        customer_email="valeria@example.com",
        starts_at=starts_utc,
        ends_at=ends_utc,
        duration_minutes=45,
        service_name="Consulta General",
        provider_name="Dra. Valenzuela",
        business_name="Estudio Nómada",
        business_timezone="America/Santiago",
        business_address="Av. Providencia 1234, Santiago",
        business_phone="+56912345678",
    )

    # 1. Subject
    subject = render_booking_confirmation_subject(booking)
    assert subject == "Confirmación de reserva en Estudio Nómada"

    # 2. Plain Text
    text = render_booking_confirmation_text(booking)
    assert "Hola Valeria Soto," in text
    assert "Servicio: Consulta General" in text
    assert "Profesional: Dra. Valenzuela" in text
    assert "Fecha: lunes, 10 de agosto de 2026" in text
    assert "Horario: 22:00 a 22:45 (Hora local America/Santiago)" in text
    assert "Duración: 45 minutos" in text
    assert "Código de reserva: REF123456" in text
    assert "Dirección: Av. Providencia 1234, Santiago" in text
    assert "Teléfono de contacto: +56912345678" in text

    # Ensure no prices or cancellation links are present
    assert "$" not in text
    assert "cancelar" not in text.lower()

    # 3. HTML
    html_content = render_booking_confirmation_html(booking)
    assert "Estudio Nómada" in html_content
    assert "Valeria Soto" in html_content
    assert "Consulta General" in html_content
    assert "Dra. Valenzuela" in html_content
    assert "lunes, 10 de agosto de 2026" in html_content
    assert "22:00 a 22:45 (Hora local America/Santiago)" in html_content
    assert "45 minutos" in html_content
    assert "REF123456" in html_content
    assert "Av. Providencia 1234, Santiago" in html_content
    assert "+56912345678" in html_content


def test_render_templates_without_optional_contact_info():
    starts_utc = datetime(2026, 8, 12, 14, 0, tzinfo=timezone.utc)
    ends_utc = datetime(2026, 8, 12, 15, 0, tzinfo=timezone.utc)

    booking = BookingEmailData(
        booking_id=uuid.uuid4(),
        public_reference="REF789",
        customer_name="Carlos Gomez",
        customer_email="carlos@example.com",
        starts_at=starts_utc,
        ends_at=ends_utc,
        duration_minutes=60,
        service_name="Terapia",
        provider_name="Dr. Martin",
        business_name="Clínica Central",
        business_timezone="America/Santiago",
        business_address=None,
        business_phone=None,
    )

    text = render_booking_confirmation_text(booking)
    assert "Dirección:" not in text
    assert "Teléfono" not in text

    html_content = render_booking_confirmation_html(booking)
    assert "Dirección:" not in html_content
    assert "Teléfono:" not in html_content


def test_console_email_service_output_privacy(capsys):
    from app.integrations.email.service import ConsoleEmailService, EmailDeliveryStatus

    booking = BookingEmailData(
        booking_id=uuid.uuid4(),
        public_reference="REF999AAA",
        customer_name="Valeria Soto",
        customer_email="valeria@example.com",
        starts_at=datetime(2026, 8, 12, 14, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 8, 12, 14, 45, tzinfo=timezone.utc),
        duration_minutes=45,
        service_name="Consulta General",
        provider_name="Dra. Valenzuela",
        business_name="Estudio Nómada",
        business_timezone="America/Santiago",
        business_address="Av. Providencia 1234, Santiago",
        business_phone="+56912345678",
    )

    svc = ConsoleEmailService()
    result = svc.send_booking_confirmation(booking)
    assert result.status == EmailDeliveryStatus.sent

    captured = capsys.readouterr().out

    # Must contain provider, masked recipient, and public reference
    assert "provider=console" in captured
    assert "v*****a@example.com" in captured
    assert "REF999AAA" in captured

    # Must NOT contain raw PII, phone, address, or email body
    assert "valeria@example.com" not in captured
    assert "Valeria Soto" not in captured
    assert "+56912345678" not in captured
    assert "Av. Providencia 1234" not in captured
    assert "<html>" not in captured.lower()
    assert "detalles de la cita" not in captured.lower()
