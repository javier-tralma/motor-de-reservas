import hashlib
import hmac
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.rate_limit import RateLimit


class RateLimitError(Exception):
    def __init__(self, code: str, message: str, status_code: int, retry_after: int | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retry_after = retry_after
        super().__init__(message)


class RateLimitExceededError(RateLimitError):
    def __init__(self, retry_after: int):
        super().__init__(
            code="rate_limit_exceeded",
            message="Has excedido el límite de solicitudes. Intenta de nuevo más tarde.",
            status_code=429,
            retry_after=retry_after,
        )


class RateLimitUnavailableError(RateLimitError):
    def __init__(self, message: str = "Servicio de verificación de límites no disponible temporalmente."):
        super().__init__(
            code="rate_limit_unavailable",
            message=message,
            status_code=503,
        )


def normalize_ip(raw_ip: str | None) -> str:
    if not raw_ip or not raw_ip.strip():
        return "unknown-client"
    ip = raw_ip.strip().lower()
    if ip.startswith("::ffff:"):
        ip = ip[7:]
    return ip


def get_subject_hash(raw_ip: str | None, secret: str) -> str:
    normalized = normalize_ip(raw_ip)
    return hmac.new(secret.encode("utf-8"), normalized.encode("utf-8"), hashlib.sha256).hexdigest()


class RateLimiter:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        secret: str,
        get_now_fn: Callable[[], datetime] | None = None,
    ):
        self.session_factory = session_factory
        self.secret = secret
        self.get_now_fn = get_now_fn

    def _get_now(self) -> datetime:
        if self.get_now_fn is not None:
            now = self.get_now_fn()
        else:
            now = datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return now

    def consume(
        self,
        endpoint: str,
        subject_hash: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int, int]:
        """
        Consumes one unit for (subject_hash, endpoint) within the fixed window.
        Opens, commits/rolls back, and closes a dedicated short session via session_factory.
        Returns: (is_allowed, current_count, retry_after_seconds)
        Raises RateLimitUnavailableError on database error (fail-closed).
        """
        now = self._get_now()
        now_epoch = int(now.timestamp())
        window_start_epoch = (now_epoch // window_seconds) * window_seconds
        window_start = datetime.fromtimestamp(window_start_epoch, tz=timezone.utc)
        cutoff = now - timedelta(seconds=window_seconds * 2)
        retry_after = max(1, window_start_epoch + window_seconds - now_epoch)

        session: Session | None = None
        try:
            session = self.session_factory()
            # Deterministic cleanup using cutoff
            session.execute(delete(RateLimit).where(RateLimit.window_start < cutoff))

            # Atomic upsert
            stmt = (
                pg_insert(RateLimit)
                .values(
                    subject_hash=subject_hash,
                    endpoint=endpoint,
                    window_start=window_start,
                    count=1,
                )
                .on_conflict_do_update(
                    constraint="pk_rate_limits",
                    set_={"count": RateLimit.count + 1},
                    where=(RateLimit.count < limit),
                )
                .returning(RateLimit.count)
            )

            result = session.execute(stmt).scalar_one_or_none()
            session.commit()

            if result is not None:
                return True, result, retry_after
            else:
                return False, limit, retry_after

        except Exception as e:
            if session is not None:
                try:
                    session.rollback()
                except Exception:
                    pass
            raise RateLimitUnavailableError() from e
        finally:
            if session is not None:
                try:
                    session.close()
                except Exception:
                    pass
