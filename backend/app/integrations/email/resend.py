import logging
from typing import Optional

import httpx

from app.integrations.email.service import BookingEmailData, EmailDeliveryStatus, EmailResult, mask_email
from app.integrations.email.templates import (
    render_booking_confirmation_html,
    render_booking_confirmation_subject,
    render_booking_confirmation_text,
)

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


class ResendEmailService:
    def __init__(
        self,
        api_key: str,
        from_email: str,
        client: Optional[httpx.Client] = None,
        timeout: float = 10.0,
    ):
        if not api_key:
            raise ValueError("api_key must not be empty for ResendEmailService")
        if not from_email:
            raise ValueError("from_email must not be empty for ResendEmailService")

        self.api_key = api_key
        self.from_email = from_email
        self._client = client
        self.timeout = timeout

    def send_booking_confirmation(self, booking: BookingEmailData) -> EmailResult:
        subject = render_booking_confirmation_subject(booking)
        text_content = render_booking_confirmation_text(booking)
        html_content = render_booking_confirmation_html(booking)

        payload = {
            "from": self.from_email,
            "to": [booking.customer_email],
            "subject": subject,
            "html": html_content,
            "text": text_content,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        masked_to = mask_email(booking.customer_email)

        try:
            if self._client is not None:
                response = self._client.post(RESEND_API_URL, json=payload, headers=headers)
            else:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(RESEND_API_URL, json=payload, headers=headers)

            if response.status_code in (200, 201):
                try:
                    data = response.json()
                    provider_id = data.get("id")
                    if not provider_id:
                        logger.warning("Resend returned 200/201 without id for %s", masked_to)
                        return EmailResult(status=EmailDeliveryStatus.failed, error_code="resend_invalid_response")
                    logger.info("Confirmation email sent via Resend for %s (id: %s)", masked_to, provider_id)
                    return EmailResult(status=EmailDeliveryStatus.sent, provider_id=str(provider_id))
                except Exception:
                    logger.warning(
                        "Resend returned invalid JSON for %s with status %d", masked_to, response.status_code
                    )
                    return EmailResult(status=EmailDeliveryStatus.failed, error_code="resend_invalid_response")
            else:
                if 400 <= response.status_code < 500:
                    error_code = "resend_http_4xx"
                elif 500 <= response.status_code < 600:
                    error_code = "resend_http_5xx"
                else:
                    error_code = "resend_http_4xx"

                logger.warning(
                    "Resend API rejected email for %s with status %d: %s",
                    masked_to,
                    response.status_code,
                    error_code,
                )
                return EmailResult(status=EmailDeliveryStatus.failed, error_code=error_code)

        except httpx.TimeoutException:
            logger.error("Resend request timed out for %s", masked_to)
            return EmailResult(status=EmailDeliveryStatus.failed, error_code="resend_timeout")
        except httpx.NetworkError, httpx.RequestError:
            logger.error("Resend network error for %s", masked_to)
            return EmailResult(status=EmailDeliveryStatus.failed, error_code="resend_network_error")
        except Exception:
            logger.error("Resend request failed with unexpected exception for %s", masked_to)
            return EmailResult(status=EmailDeliveryStatus.failed, error_code="resend_network_error")
