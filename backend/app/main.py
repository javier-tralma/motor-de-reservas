import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.admin import auth as admin_auth
from app.api.admin import bookings as admin_bookings
from app.api.admin import calendar_events as admin_calendar_events
from app.api.admin import dashboard as admin_dashboard
from app.api.admin import providers as admin_providers
from app.api.admin import services as admin_services
from app.api.admin import time_off as admin_time_off
from app.api.endpoints import availability, bookings, public
from app.api.endpoints.availability import DomainError
from app.core.config import settings
from app.core.rate_limit import RateLimitError
from app.services.auth_service import AuthError

app = FastAPI(title="Booking API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public.router, prefix="/api")
app.include_router(availability.router, prefix="/api")
app.include_router(bookings.router, prefix="/api")
app.include_router(admin_auth.router, prefix="/api/admin")
app.include_router(admin_dashboard.router, prefix="/api/admin")
app.include_router(admin_bookings.router, prefix="/api/admin")
app.include_router(admin_providers.router, prefix="/api/admin")
app.include_router(admin_services.router, prefix="/api/admin")
app.include_router(admin_time_off.router, prefix="/api/admin")
app.include_router(admin_calendar_events.router, prefix="/api/admin")


@app.exception_handler(RateLimitError)
async def rate_limit_error_handler(request: Request, exc: RateLimitError):
    headers = {}
    if exc.retry_after is not None:
        headers["Retry-After"] = str(exc.retry_after)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": {}, "request_id": str(uuid.uuid4())}},
        headers=headers,
    )


@app.exception_handler(AuthError)
async def auth_error_handler(request: Request, exc: AuthError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": {}, "request_id": str(uuid.uuid4())}},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        code = exc.detail["code"]
        message = exc.detail.get("message", "Error de servidor.")
        details = exc.detail.get("details", {})
    else:
        code = f"http_{exc.status_code}"
        message = str(exc.detail) if exc.detail else "Error en la petición."
        details = {}

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": message, "details": details, "request_id": str(uuid.uuid4())}},
        headers=exc.headers,
    )


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": {}, "request_id": str(uuid.uuid4())}},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Invalid request parameters",
                "details": jsonable_encoder(exc.errors()),
                "request_id": str(uuid.uuid4()),
            }
        },
    )


@app.get("/health")
def health_check():
    return {"status": "ok"}
