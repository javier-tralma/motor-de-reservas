from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    BUSINESS_ID: str
    FRONTEND_URL: str
    APP_ENV: str = "development"
    SESSION_SECRET: str = ""
    ADMIN_SESSION_TTL_HOURS: int = 8
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""
    ADMIN_DISPLAY_NAME: str = ""

    # Email configuration
    EMAIL_PROVIDER: str = "console"
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "reservas@estudionomada.cl"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def validate_session_settings(self) -> "Settings":
        if self.APP_ENV.lower() == "production" and not self.SESSION_SECRET:
            raise ValueError("SESSION_SECRET must be set in production environment")
        if self.ADMIN_SESSION_TTL_HOURS <= 0:
            raise ValueError("ADMIN_SESSION_TTL_HOURS must be greater than 0")
        return self

    @model_validator(mode="after")
    def validate_email_settings(self) -> "Settings":
        provider = self.EMAIL_PROVIDER.lower().strip()
        if provider not in ("console", "noop", "resend"):
            raise ValueError(f"EMAIL_PROVIDER must be one of 'console', 'noop', 'resend', got '{self.EMAIL_PROVIDER}'")

        if self.APP_ENV.lower() == "production":
            if provider != "resend":
                raise ValueError("EMAIL_PROVIDER must be 'resend' in production environment")
            if not self.RESEND_API_KEY.strip():
                raise ValueError("RESEND_API_KEY must be set in production environment")
            if not self.EMAIL_FROM.strip():
                raise ValueError("EMAIL_FROM must be set in production environment")
        elif provider == "resend":
            if not self.RESEND_API_KEY.strip():
                raise ValueError("RESEND_API_KEY must be set when EMAIL_PROVIDER is 'resend'")
            if not self.EMAIL_FROM.strip():
                raise ValueError("EMAIL_FROM must be set when EMAIL_PROVIDER is 'resend'")
        return self


settings = Settings()
