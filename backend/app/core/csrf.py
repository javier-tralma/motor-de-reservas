from fastapi import HTTPException, Request, status

from app.core.config import settings


def verify_origin(request: Request) -> None:
    """Verify that Origin header matches FRONTEND_URL for mutative requests."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    origin = request.headers.get("origin")
    frontend_url = settings.FRONTEND_URL.rstrip("/")

    if not origin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "origin_mismatch",
                "message": "Petición rechazada: encabezado Origin ausente.",
            },
        )

    normalized_origin = origin.rstrip("/")
    if normalized_origin != frontend_url:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "origin_mismatch",
                "message": f"Petición rechazada: Origin '{origin}' no coincide con '{frontend_url}'.",
            },
        )
