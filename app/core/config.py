import os
from pydantic_settings import BaseSettings
from typing import List, Optional

APP_ENV = os.getenv("APP_ENV", "dev")


class Settings(BaseSettings):
    PROJECT_NAME: str = "Fourhub Timesheet"
    API_V1_STR: str = "/api/v1"
    APP_ENV: str = APP_ENV

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Defaults cover all environments for local dev; each Railway env overrides via its own .env file
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://timesheet.fourhubtech.com",
        "https://dev.timekeepinghub.com",
        "https://qa.timekeepinghub.com",
        "https://preview.timekeepinghub.com",
        "https://timekeepinghub.com",
    ]

    # Email (SMTP) — leave blank to disable email sending
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_NAME: str = "Fourhub Timesheet"
    SMTP_FROM_EMAIL: str = "noreply@fourhubtech.com"

    class Config:
        env_file = f".env.{APP_ENV}"
        case_sensitive = True


settings = Settings()
