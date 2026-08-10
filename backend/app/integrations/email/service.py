from datetime import datetime
from typing import Optional, Protocol
from uuid import UUID

from pydantic import BaseModel

from app.models.booking import EmailDeliveryStatus


class BookingEmailData(BaseModel):
    booking_id: UUID
    public_reference: str
    customer_name: str
    customer_email: str
    starts_at: datetime
    ends_at: datetime
    service_name: str
    provider_name: str
    business_name: str
    business_timezone: str


class EmailResult(BaseModel):
    status: EmailDeliveryStatus
    provider_id: Optional[str] = None
    error_code: Optional[str] = None


class EmailService(Protocol):
    def send_booking_confirmation(self, booking: BookingEmailData) -> EmailResult: ...


class ConsoleEmailService:
    def send_booking_confirmation(self, booking: BookingEmailData) -> EmailResult:
        masked_email = (
            booking.customer_email[0] + "***" + booking.customer_email[booking.customer_email.find("@") :]
            if "@" in booking.customer_email
            else "***"
        )
        masked_name = booking.customer_name[0] + "***" if booking.customer_name else "***"

        print(f"--- EMAIL TO: {masked_email} ---")
        print(f"Subject: Confirmación de reserva en {booking.business_name}")
        print(f"Hola {masked_name},")
        print(f"Tu cita para {booking.service_name} con {booking.provider_name}")
        print(f"está confirmada para el {booking.starts_at}.")
        print(f"Referencia de reserva: {booking.public_reference}")
        print("---------------------------------------")
        return EmailResult(status=EmailDeliveryStatus.sent, provider_id="console-dev")


class NoOpEmailService:
    def send_booking_confirmation(self, booking: BookingEmailData) -> EmailResult:
        return EmailResult(status=EmailDeliveryStatus.sent, provider_id="noop")


class FakeEmailService:
    def __init__(self):
        self.should_fail = False
        self.should_raise = False
        self.sent_emails = []

    def send_booking_confirmation(self, booking: BookingEmailData) -> EmailResult:
        if self.should_raise:
            raise RuntimeError("Fake network exception")
        self.sent_emails.append(booking)
        if self.should_fail:
            return EmailResult(status=EmailDeliveryStatus.failed, error_code="fake_network_error")
        return EmailResult(status=EmailDeliveryStatus.sent, provider_id="fake-id-123")
