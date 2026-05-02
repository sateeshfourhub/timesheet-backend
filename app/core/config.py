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
    SUPER_ADMIN_TOKEN: str = ""
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

    # Email (Resend) — leave RESEND_API_KEY blank to disable email sending
    RESEND_API_KEY: Optional[str] = None
    EMAIL_FROM: str = "noreply@timekeepinghub.com"
    EMAIL_REPLY_TO: str = "support@timekeepinghub.com"
    EMAIL_DEV_RECIPIENT: Optional[str] = None  # if set, all emails go here instead of real recipient
    FRONTEND_URL: str = "https://timekeepinghub.com"

    class Config:
        env_file = f".env.{APP_ENV}"
        case_sensitive = True


settings = Settings()
