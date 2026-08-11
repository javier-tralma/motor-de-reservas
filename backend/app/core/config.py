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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def validate_session_settings(self) -> "Settings":
        if self.APP_ENV.lower() == "production" and not self.SESSION_SECRET:
            raise ValueError("SESSION_SECRET must be set in production environment")
        if self.ADMIN_SESSION_TTL_HOURS <= 0:
            raise ValueError("ADMIN_SESSION_TTL_HOURS must be greater than 0")
        return self


settings = Settings()
