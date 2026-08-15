from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.core.rate_limit import (
    RateLimiter,
    RateLimitUnavailableError,
    get_subject_hash,
    normalize_ip,
)


def test_normalize_ip():
    assert normalize_ip("192.168.1.1") == "192.168.1.1"
    assert normalize_ip("  192.168.1.1  ") == "192.168.1.1"
    assert normalize_ip("::ffff:192.168.1.1") == "192.168.1.1"
    assert normalize_ip(None) == "unknown-client"
    assert normalize_ip("") == "unknown-client"
    assert normalize_ip("   ") == "unknown-client"


def test_get_subject_hash_stable_and_secret_sensitive():
    secret1 = "secret-key-1"
    secret2 = "secret-key-2"
    ip = "192.168.1.50"

    hash1 = get_subject_hash(ip, secret1)
    hash2 = get_subject_hash(ip, secret1)
    hash_diff_secret = get_subject_hash(ip, secret2)
    hash_diff_ip = get_subject_hash("192.168.1.51", secret1)

    assert hash1 == hash2
    assert len(hash1) == 64
    assert hash1 != hash_diff_secret
    assert hash1 != hash_diff_ip


def test_rate_limiter_consume_with_mock_clock():
    from tests.conftest import TestingSessionLocal

    secret = "test-secret"
    fixed_time = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
    current_time = fixed_time

    def get_now():
        return current_time

    limiter = RateLimiter(session_factory=TestingSessionLocal, secret=secret, get_now_fn=get_now)
    subject = get_subject_hash("10.0.0.1", secret)

    # Consume up to limit of 3 in a 60-second window
    allowed1, count1, retry_after1 = limiter.consume("test_ep", subject, limit=3, window_seconds=60)
    assert allowed1 is True
    assert count1 == 1
    assert retry_after1 == 60

    allowed2, count2, _ = limiter.consume("test_ep", subject, limit=3, window_seconds=60)
    assert allowed2 is True
    assert count2 == 2

    allowed3, count3, _ = limiter.consume("test_ep", subject, limit=3, window_seconds=60)
    assert allowed3 is True
    assert count3 == 3

    # 4th request exceeds limit
    allowed4, count4, retry_after4 = limiter.consume("test_ep", subject, limit=3, window_seconds=60)
    assert allowed4 is False
    assert count4 == 3
    assert retry_after4 == 60

    # Advance clock by 30 seconds (still in same window)
    current_time = fixed_time + timedelta(seconds=30)
    allowed5, count5, retry_after5 = limiter.consume("test_ep", subject, limit=3, window_seconds=60)
    assert allowed5 is False
    assert retry_after5 == 30

    # Advance clock by 61 seconds (new window)
    current_time = fixed_time + timedelta(seconds=61)
    allowed6, count6, retry_after6 = limiter.consume("test_ep", subject, limit=3, window_seconds=60)
    assert allowed6 is True
    assert count6 == 1
    assert retry_after6 == 59


def test_rate_limiter_session_isolation_and_distinct_lifecycle():
    """Verify that RateLimiter uses its own dedicated session and does not touch use-case session."""
    mock_limiter_session = MagicMock()
    mock_limiter_session.execute.return_value.scalar_one_or_none.return_value = 1
    session_factory = MagicMock(return_value=mock_limiter_session)

    limiter = RateLimiter(session_factory=session_factory, secret="test-secret")

    # Use-case session used by domain service (e.g. BookingService)
    use_case_session = MagicMock()

    allowed, count, _ = limiter.consume("test_ep", "subject_hash", limit=5, window_seconds=60)

    assert allowed is True
    assert count == 1

    # Verify limiter session was opened, committed, and closed
    session_factory.assert_called_once()
    mock_limiter_session.commit.assert_called_once()
    mock_limiter_session.close.assert_called_once()

    # Verify use_case_session was completely untouched by RateLimiter
    use_case_session.execute.assert_not_called()
    use_case_session.commit.assert_not_called()
    use_case_session.rollback.assert_not_called()
    use_case_session.close.assert_not_called()


def test_rate_limiter_fail_closed_on_db_error():
    mock_session = MagicMock()
    mock_session.execute.side_effect = Exception("DB connection dropped")
    session_factory = MagicMock(return_value=mock_session)

    limiter = RateLimiter(session_factory=session_factory, secret="test-secret")
    with pytest.raises(RateLimitUnavailableError) as exc_info:
        limiter.consume("test_ep", "subject_hash", limit=5, window_seconds=60)

    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "rate_limit_unavailable"
    mock_session.rollback.assert_called_once()
    mock_session.close.assert_called_once()


def test_rate_limiter_fail_closed_when_session_factory_fails():
    """Verify fail-closed with 503 RateLimitUnavailableError when session_factory itself raises."""
    session_factory = MagicMock(side_effect=Exception("Database pool exhausted or connection refused"))

    limiter = RateLimiter(session_factory=session_factory, secret="test-secret")
    with pytest.raises(RateLimitUnavailableError) as exc_info:
        limiter.consume("test_ep", "subject_hash", limit=5, window_seconds=60)

    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "rate_limit_unavailable"
    session_factory.assert_called_once()
