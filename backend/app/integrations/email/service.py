import logging
from datetime import datetime
from typing import Optional, Protocol
from uuid import UUID

from pydantic import BaseModel

from app.models.booking import EmailDeliveryStatus

logger = logging.getLogger(__name__)


def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "*" if local else "*"
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked_local}@{domain}"


def mask_name(name: str) -> str:
    if not name:
        return "***"
    return name[0] + "***" if len(name) > 1 else name + "***"


class BookingEmailData(BaseModel):
    booking_id: UUID
    public_reference: str
    customer_name: str
    customer_email: str
    starts_at: datetime
    ends_at: datetime
    duration_minutes: int
    service_name: str
    provider_name: str
    business_name: str
    business_timezone: str
    business_address: Optional[str] = None
    business_phone: Optional[str] = None


class EmailResult(BaseModel):
    status: EmailDeliveryStatus
    provider_id: Optional[str] = None
    error_code: Optional[str] = None


class EmailService(Protocol):
    def send_booking_confirmation(self, booking: BookingEmailData) -> EmailResult: ...


class ConsoleEmailService:
    def send_booking_confirmation(self, booking: BookingEmailData) -> EmailResult:
        masked_to = mask_email(booking.customer_email)
        print(f"[CONSOLE EMAIL] provider=console recipient={masked_to} reference={booking.public_reference}")
        return EmailResult(status=EmailDeliveryStatus.sent, provider_id="console-dev")


class NoOpEmailService:
    def send_booking_confirmation(self, booking: BookingEmailData) -> EmailResult:
        logger.debug("NoOpEmailService: email skipped for %s", mask_email(booking.customer_email))
        return EmailResult(status=EmailDeliveryStatus.sent, provider_id="noop")


class FakeEmailService:
    def __init__(self):
        self.should_fail = False
        self.should_raise = False
        self.sent_emails: list[BookingEmailData] = []

    def send_booking_confirmation(self, booking: BookingEmailData) -> EmailResult:
        if self.should_raise:
            raise RuntimeError("Fake network exception")
        self.sent_emails.append(booking)
        if self.should_fail:
            return EmailResult(status=EmailDeliveryStatus.failed, error_code="fake_network_error")
        return EmailResult(status=EmailDeliveryStatus.sent, provider_id="fake-id-123")
