import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

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

# Monorepo static dist path
FRONTEND_DIST_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

app = FastAPI(title="Booking API", docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. API routers
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


# 2. System endpoints
@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/live")
def health_live():
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready():
    return {"status": "ok"}


# 3. Exception handlers
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


# 4. SPA Fallback and Static File Handler for non-API GET requests
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa_fallback(full_path: str):
    dist_dir = FRONTEND_DIST_DIR.resolve()

    # Non-API / non-assets routes when frontend/dist is not built
    if not dist_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "Ruta no encontrada (dist no disponible)."},
        )

    # Do not serve index.html for unmatched API routes
    if full_path == "api" or full_path.startswith("api/"):
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "Endpoint de API no encontrado."},
        )

    # For assets/ paths: serve if file exists, else return 404 (never index.html)
    if full_path.startswith("assets/"):
        candidate_asset = (dist_dir / full_path).resolve()
        if (dist_dir in candidate_asset.parents or candidate_asset == dist_dir) and candidate_asset.is_file():
            return FileResponse(str(candidate_asset))
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "Asset estático no encontrado."},
        )

    # Check for exact root-level static files (favicon.ico, vite.svg, robots.txt)
    if full_path:
        candidate_file = (dist_dir / full_path).resolve()
        if (dist_dir in candidate_file.parents or candidate_file == dist_dir) and candidate_file.is_file():
            return FileResponse(str(candidate_file))

    # SPA index.html fallback for client-side routing
    index_file = dist_dir / "index.html"
    if index_file.is_file():
        return FileResponse(str(index_file))

    raise HTTPException(
        status_code=404,
        detail={"code": "not_found", "message": "Archivo index.html no encontrado."},
    )
