from typing import TYPE_CHECKING

from app.integrations.email.resend import ResendEmailService
from app.integrations.email.service import ConsoleEmailService, EmailService, NoOpEmailService

if TYPE_CHECKING:
    from app.core.config import Settings


def get_email_service(settings: "Settings") -> EmailService:
    provider = settings.EMAIL_PROVIDER.lower().strip()
    if provider == "resend":
        if not settings.RESEND_API_KEY:
            raise ValueError("RESEND_API_KEY is required when EMAIL_PROVIDER is 'resend'")
        return ResendEmailService(
            api_key=settings.RESEND_API_KEY,
            from_email=settings.EMAIL_FROM,
        )
    elif provider == "noop":
        return NoOpEmailService()
    elif provider == "console":
        return ConsoleEmailService()
    else:
        raise ValueError(f"Unknown EMAIL_PROVIDER: {settings.EMAIL_PROVIDER}")
