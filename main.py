from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/debug/email")
def debug_email():
    from app.core.email import _send
    has_key = bool(settings.RESEND_API_KEY)
    result = _send(
        to="debug@example.com",
        subject="Debug test — TimekeepingHub",
        html_body="<p>Debug test email from Railway deployment.</p>",
    )
    return {
        "has_resend_key": has_key,
        "key_preview": settings.RESEND_API_KEY[:10] + "..." if has_key else None,
        "email_from": settings.EMAIL_FROM,
        "dev_recipient": settings.EMAIL_DEV_RECIPIENT,
        "app_env": settings.APP_ENV,
        "send_result": result,
    }
