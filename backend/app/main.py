import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.endpoints import availability, bookings, public
from app.api.endpoints.availability import DomainError
from app.core.config import settings

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
                "details": exc.errors(),
                "request_id": str(uuid.uuid4()),
            }
        },
    )


@app.get("/health")
def health_check():
    return {"status": "ok"}
