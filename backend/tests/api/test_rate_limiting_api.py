import threading
import uuid
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from pwdlib import PasswordHash
from sqlalchemy import delete, func, select

from app.core.config import settings
from app.core.dependencies import get_session_factory
from app.core.rate_limit import get_subject_hash
from app.domain.availability import AvailabilityEngine
from app.integrations.email.service import FakeEmailService
from app.main import app
from app.models.admin_session import AdminSession
from app.models.admin_user import AdminUser
from app.models.availability import AvailabilityRule
from app.models.booking import Booking
from app.models.business import Business
from app.models.provider import Provider, ProviderService
from app.models.rate_limit import RateLimit
from app.models.service import Service
from app.services.availability_service import AvailabilityService
from app.services.booking_service import BookingService
from tests.conftest import TestingSessionLocal


def test_public_booking_barrier_concurrency_rate_limiting():
    """
    Real multithreaded concurrency test with threading.Barrier:
    6 concurrent threads sending valid, non-overlapping booking requests.
    Exactly 5 must receive 201 Created and 1 must receive 429 RateLimitExceeded.
    Persisted count in DB must be exactly 5.
    No sleep used.
    """
    b_id = uuid.uuid4()
    p_id = uuid.uuid4()
    s_id = uuid.uuid4()

    unique_suffix = uuid.uuid4().hex[:8]
    slug = f"concurrent-rl-biz-{unique_suffix}"

    try:
        with TestingSessionLocal() as setup_db:
            business = Business(
                id=b_id,
                name=f"Concurrent RL Biz {unique_suffix}",
                slug=slug,
                email=f"biz-{unique_suffix}@test.com",
                timezone="America/Santiago",
            )
            provider = Provider(id=p_id, business_id=b_id, name="Test Provider")
            service = Service(id=s_id, business_id=b_id, name="Test Service", duration_minutes=30, price_amount=1000)
            ps = ProviderService(business_id=b_id, provider_id=p_id, service_id=s_id)

            target_date = date(2026, 8, 17)
            rule = AvailabilityRule(
                id=uuid.uuid4(),
                business_id=b_id,
                provider_id=p_id,
                weekday=target_date.weekday(),
                start_time=time(8, 0),
                end_time=time(20, 0),
            )
            setup_db.add_all([business, provider, service, ps, rule])
            setup_db.commit()

        orig_biz_id = settings.BUSINESS_ID
        settings.BUSINESS_ID = str(b_id)

        from app.api.endpoints.bookings import get_booking_service
        from app.core.db import get_db

        fake_email = FakeEmailService()

        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        def override_session_factory():
            return TestingSessionLocal

        def override_booking_service():
            db = TestingSessionLocal()
            try:
                engine = AvailabilityEngine(get_now_fn=lambda tz="UTC": datetime(2026, 8, 1, tzinfo=timezone.utc))
                availability_service = AvailabilityService(db, engine=engine)
                yield BookingService(db, availability_service, fake_email)
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_session_factory] = override_session_factory
        app.dependency_overrides[get_booking_service] = override_booking_service

        local_tz = ZoneInfo("America/Santiago")
        times = [time(9, 0), time(10, 0), time(11, 0), time(12, 0), time(13, 0), time(14, 0)]
        client_req_ids = [str(uuid.uuid4()) for _ in range(6)]

        barrier = threading.Barrier(6, timeout=10.0)
        results: list[dict] = []
        thread_exceptions: list[Exception] = []
        results_lock = threading.Lock()

        def worker(idx: int):
            try:
                starts_at_local = datetime.combine(target_date, times[idx], tzinfo=local_tz)
                payload = {
                    "service_id": str(s_id),
                    "provider_id": str(p_id),
                    "starts_at": starts_at_local.isoformat(),
                    "client_request_id": client_req_ids[idx],
                    "customer_name": f"Customer {idx}",
                    "customer_email": f"cust{idx}@example.com",
                    "customer_phone": "+56911112222",
                    "customer_notes": "",
                }

                # Synchronize all threads at the barrier
                barrier.wait()

                # Each thread uses its own client
                with TestClient(app) as thread_client:
                    res = thread_client.post("/api/public/bookings", json=payload)
                    with results_lock:
                        results.append({"status_code": res.status_code, "json": res.json()})
            except Exception as exc:
                with results_lock:
                    thread_exceptions.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)
            if t.is_alive():
                pytest.fail("Thread timed out waiting for execution")

        if thread_exceptions:
            pytest.fail(f"Exceptions occurred in worker threads: {thread_exceptions}")

        status_codes = [r["status_code"] for r in results]
        assert status_codes.count(201) == 5, f"Expected 5 successes (201), got: {status_codes}"
        assert status_codes.count(429) == 1, f"Expected 1 rate limit (429), got: {status_codes}"

        # Verify rate limit counter in database is exactly 5
        subject_hash = get_subject_hash("testclient", settings.RATE_LIMIT_SECRET)
        with TestingSessionLocal() as check_db:
            rl_row = check_db.execute(
                select(RateLimit).filter_by(endpoint="public_booking", subject_hash=subject_hash)
            ).scalar_one()
            assert rl_row.count == 5

    finally:
        settings.BUSINESS_ID = orig_biz_id
        app.dependency_overrides.clear()
        with TestingSessionLocal() as cleanup_db:
            cleanup_db.execute(delete(Booking).where(Booking.business_id == b_id))
            cleanup_db.execute(delete(AvailabilityRule).where(AvailabilityRule.business_id == b_id))
            cleanup_db.execute(delete(ProviderService).where(ProviderService.business_id == b_id))
            cleanup_db.execute(delete(Provider).where(Provider.business_id == b_id))
            cleanup_db.execute(delete(Service).where(Service.business_id == b_id))
            cleanup_db.execute(delete(Business).where(Business.id == b_id))
            cleanup_db.commit()


def test_incompatible_idempotency_consumes_quota_and_returns_409(client, db_session):
    """
    Verify that an incompatible replay:
    1. Returns 409 idempotency_conflict
    2. Consumes 1 unit of rate limit quota
    3. Does not create a second booking
    """
    b_id = uuid.uuid4()
    p_id = uuid.uuid4()
    s_id = uuid.uuid4()

    business = Business(
        id=b_id, name="Incomp Idempotency Biz", slug="incomp-rl-biz", email="biz@test.com", timezone="America/Santiago"
    )
    provider = Provider(id=p_id, business_id=b_id, name="Test Provider")
    service = Service(id=s_id, business_id=b_id, name="Test Service", duration_minutes=30, price_amount=1000)
    ps = ProviderService(business_id=b_id, provider_id=p_id, service_id=s_id)

    target_date = date(2026, 8, 17)
    rule = AvailabilityRule(
        id=uuid.uuid4(),
        business_id=b_id,
        provider_id=p_id,
        weekday=target_date.weekday(),
        start_time=time(8, 0),
        end_time=time(20, 0),
    )
    db_session.add_all([business, provider, service, ps, rule])
    db_session.commit()

    orig_biz_id = settings.BUSINESS_ID
    settings.BUSINESS_ID = str(business.id)

    from app.api.endpoints.bookings import get_booking_service

    fake_email = FakeEmailService()

    def override_booking_service():
        engine = AvailabilityEngine(get_now_fn=lambda tz="UTC": datetime(2026, 8, 1, tzinfo=timezone.utc))
        availability_service = AvailabilityService(db_session, engine=engine)
        yield BookingService(db_session, availability_service, fake_email)

    app.dependency_overrides[get_booking_service] = override_booking_service

    local_tz = ZoneInfo(business.timezone)
    starts_at_1 = datetime.combine(target_date, time(10, 0), tzinfo=local_tz)
    shared_client_req_id = str(uuid.uuid4())

    try:
        # Step 1: Initial valid booking
        payload_1 = {
            "service_id": str(service.id),
            "provider_id": str(provider.id),
            "starts_at": starts_at_1.isoformat(),
            "client_request_id": shared_client_req_id,
            "customer_name": "Original Customer",
            "customer_email": "original@example.com",
            "customer_phone": "+56911112222",
            "customer_notes": "",
        }
        res_1 = client.post("/api/public/bookings", json=payload_1)
        assert res_1.status_code == 201, res_1.text

        # Rate limit count is 1
        subject_hash = get_subject_hash("testclient", settings.RATE_LIMIT_SECRET)
        rl_1 = db_session.execute(
            select(RateLimit).filter_by(endpoint="public_booking", subject_hash=subject_hash)
        ).scalar_one()
        assert rl_1.count == 1

        # Step 2: Resend same client_request_id with different payload (incompatible replay)
        starts_at_2 = datetime.combine(target_date, time(11, 0), tzinfo=local_tz)
        payload_incompatible = {
            "service_id": str(service.id),
            "provider_id": str(provider.id),
            "starts_at": starts_at_2.isoformat(),
            "client_request_id": shared_client_req_id,
            "customer_name": "Modified Customer",
            "customer_email": "modified@example.com",
            "customer_phone": "+56911112222",
            "customer_notes": "Different notes",
        }
        res_2 = client.post("/api/public/bookings", json=payload_incompatible)
        assert res_2.status_code == 409, res_2.text
        assert res_2.json()["error"]["code"] == "idempotency_conflict"

        # Step 3: Quota count was consumed and is now 2
        db_session.expire_all()
        rl_2 = db_session.execute(
            select(RateLimit).filter_by(endpoint="public_booking", subject_hash=subject_hash)
        ).scalar_one()
        assert rl_2.count == 2

        # Step 4: Verify no second booking was created
        booking_count = db_session.execute(select(func.count(Booking.id)).filter(Booking.business_id == b_id)).scalar()
        assert booking_count == 1

    finally:
        settings.BUSINESS_ID = orig_biz_id
        app.dependency_overrides.pop(get_booking_service, None)


def test_valid_idempotency_replay_after_quota_exhaustion(client, db_session):
    """
    Verify that when rate limit quota is exhausted (5/5 requests consumed):
    A valid idempotency replay returns 200 OK and does not increase the counter or get blocked by 429.
    """
    b_id = uuid.uuid4()
    p_id = uuid.uuid4()
    s_id = uuid.uuid4()

    business = Business(
        id=b_id, name="Replay RL Biz", slug="replay-rl-biz", email="biz@test.com", timezone="America/Santiago"
    )
    provider = Provider(id=p_id, business_id=b_id, name="Test Provider")
    service = Service(id=s_id, business_id=b_id, name="Test Service", duration_minutes=30, price_amount=1000)
    ps = ProviderService(business_id=b_id, provider_id=p_id, service_id=s_id)

    target_date = date(2026, 8, 17)
    rule = AvailabilityRule(
        id=uuid.uuid4(),
        business_id=b_id,
        provider_id=p_id,
        weekday=target_date.weekday(),
        start_time=time(8, 0),
        end_time=time(20, 0),
    )
    db_session.add_all([business, provider, service, ps, rule])
    db_session.commit()

    orig_biz_id = settings.BUSINESS_ID
    settings.BUSINESS_ID = str(business.id)

    from app.api.endpoints.bookings import get_booking_service

    fake_email = FakeEmailService()

    def override_booking_service():
        engine = AvailabilityEngine(get_now_fn=lambda tz="UTC": datetime(2026, 8, 1, tzinfo=timezone.utc))
        availability_service = AvailabilityService(db_session, engine=engine)
        yield BookingService(db_session, availability_service, fake_email)

    app.dependency_overrides[get_booking_service] = override_booking_service

    local_tz = ZoneInfo(business.timezone)
    times = [time(9, 0), time(10, 0), time(11, 0), time(12, 0), time(13, 0)]
    client_req_ids = [str(uuid.uuid4()) for _ in range(5)]

    try:
        # Create 5 valid bookings to exhaust the quota
        for i in range(5):
            starts_at_local = datetime.combine(target_date, times[i], tzinfo=local_tz)
            payload = {
                "service_id": str(service.id),
                "provider_id": str(provider.id),
                "starts_at": starts_at_local.isoformat(),
                "client_request_id": client_req_ids[i],
                "customer_name": f"Customer {i}",
                "customer_email": f"cust{i}@example.com",
                "customer_phone": "+56911112222",
                "customer_notes": "",
            }
            res = client.post("/api/public/bookings", json=payload)
            assert res.status_code == 201, res.text

        # Verify DB count is 5
        subject_hash = get_subject_hash("testclient", settings.RATE_LIMIT_SECRET)
        rl_row = db_session.execute(
            select(RateLimit).filter_by(endpoint="public_booking", subject_hash=subject_hash)
        ).scalar_one()
        assert rl_row.count == 5

        # Replay request 0 with identical payload
        starts_at_0 = datetime.combine(target_date, times[0], tzinfo=local_tz)
        payload_replay = {
            "service_id": str(service.id),
            "provider_id": str(provider.id),
            "starts_at": starts_at_0.isoformat(),
            "client_request_id": client_req_ids[0],
            "customer_name": "Customer 0",
            "customer_email": "cust0@example.com",
            "customer_phone": "+56911112222",
            "customer_notes": "",
        }
        res_replay = client.post("/api/public/bookings", json=payload_replay)
        assert res_replay.status_code == 200, res_replay.text
        assert res_replay.json()["data"]["customer_email"] == "cust0@example.com"

        # Rate limit count remains 5
        db_session.expire_all()
        rl_row = db_session.execute(
            select(RateLimit).filter_by(endpoint="public_booking", subject_hash=subject_hash)
        ).scalar_one()
        assert rl_row.count == 5

    finally:
        settings.BUSINESS_ID = orig_biz_id
        app.dependency_overrides.pop(get_booking_service, None)


def test_admin_login_rate_limiting(client, db_session):
    b_id = uuid.uuid4()
    business = Business(
        id=b_id, name="Admin Auth Biz", slug="auth-biz", email="admin-biz@test.com", timezone="America/Santiago"
    )

    password_hash = PasswordHash.recommended()
    hashed = password_hash.hash("CorrectPassword123!")
    admin_user = AdminUser(
        id=uuid.uuid4(),
        business_id=b_id,
        email="admin@test.com",
        password_hash=hashed,
        display_name="Admin",
        is_active=True,
    )
    db_session.add(business)
    db_session.flush()
    db_session.add(admin_user)
    db_session.commit()

    orig_biz_id = settings.BUSINESS_ID
    settings.BUSINESS_ID = str(business.id)

    headers = {"Origin": settings.FRONTEND_URL}

    try:
        # Send 10 failed login requests (should all return 401)
        for i in range(10):
            res = client.post(
                "/api/admin/auth/login",
                json={"email": "admin@test.com", "password": f"WrongPass{i}!"},
                headers=headers,
            )
            assert res.status_code == 401, res.text
            assert res.json()["error"]["code"] == "invalid_credentials"

        # 11th request must return 429
        res_11 = client.post(
            "/api/admin/auth/login",
            json={"email": "admin@test.com", "password": "CorrectPassword123!"},
            headers=headers,
        )
        assert res_11.status_code == 429, res_11.text
        assert res_11.json()["error"]["code"] == "rate_limit_exceeded"
        assert "Retry-After" in res_11.headers

        # Check DB count never exceeds 10
        subject_hash = get_subject_hash("testclient", settings.RATE_LIMIT_SECRET)
        rl_row = db_session.execute(
            select(RateLimit).filter_by(endpoint="admin_login", subject_hash=subject_hash)
        ).scalar_one()
        assert rl_row.count == 10

        # Sending X-Forwarded-For does not change subject
        res_spoof = client.post(
            "/api/admin/auth/login",
            json={"email": "admin@test.com", "password": "CorrectPassword123!"},
            headers={**headers, "X-Forwarded-For": "203.0.113.195"},
        )
        assert res_spoof.status_code == 429

    finally:
        settings.BUSINESS_ID = orig_biz_id


def test_public_booking_fail_closed_503_when_rate_limiter_factory_fails(client, db_session):
    """
    Verify fail-closed 503 response and standard error envelope when rate limiter
    session_factory raises an exception during public booking.
    Ensures no booking is created and no confirmation email is sent.
    """
    b_id = uuid.uuid4()
    p_id = uuid.uuid4()
    s_id = uuid.uuid4()

    business = Business(
        id=b_id, name="Fail Closed Booking Biz", slug="fc-book-biz", email="biz@test.com", timezone="America/Santiago"
    )
    provider = Provider(id=p_id, business_id=b_id, name="Test Provider")
    service = Service(id=s_id, business_id=b_id, name="Test Service", duration_minutes=30, price_amount=1000)
    ps = ProviderService(business_id=b_id, provider_id=p_id, service_id=s_id)

    target_date = date(2026, 8, 17)
    rule = AvailabilityRule(
        id=uuid.uuid4(),
        business_id=b_id,
        provider_id=p_id,
        weekday=target_date.weekday(),
        start_time=time(8, 0),
        end_time=time(20, 0),
    )
    db_session.add_all([business, provider, service, ps, rule])
    db_session.commit()

    orig_biz_id = settings.BUSINESS_ID
    settings.BUSINESS_ID = str(business.id)

    from app.api.endpoints.bookings import get_booking_service

    fake_email = FakeEmailService()

    def override_booking_service():
        engine = AvailabilityEngine(get_now_fn=lambda tz="UTC": datetime(2026, 8, 1, tzinfo=timezone.utc))
        availability_service = AvailabilityService(db_session, engine=engine)
        yield BookingService(db_session, availability_service, fake_email)

    def failing_session_factory():
        raise Exception("Database connection dropped on rate limit check")

    app.dependency_overrides[get_booking_service] = override_booking_service
    app.dependency_overrides[get_session_factory] = lambda: failing_session_factory

    local_tz = ZoneInfo(business.timezone)
    starts_at = datetime.combine(target_date, time(10, 0), tzinfo=local_tz)

    try:
        payload = {
            "service_id": str(service.id),
            "provider_id": str(provider.id),
            "starts_at": starts_at.isoformat(),
            "client_request_id": str(uuid.uuid4()),
            "customer_name": "Test Customer",
            "customer_email": "test@example.com",
            "customer_phone": "+56911112222",
            "customer_notes": "",
        }
        res = client.post("/api/public/bookings", json=payload)
        assert res.status_code == 503, res.text

        # Verify complete standard error envelope
        body = res.json()
        assert "error" in body
        error = body["error"]
        assert error["code"] == "rate_limit_unavailable"
        assert error["message"] == "Servicio de verificación de límites no disponible temporalmente."
        assert "request_id" in error
        assert "details" in error

        # Verify no booking created
        db_session.expire_all()
        booking_count = db_session.execute(select(func.count(Booking.id)).filter(Booking.business_id == b_id)).scalar()
        assert booking_count == 0

        # Verify no confirmation email sent
        assert len(fake_email.sent_emails) == 0

    finally:
        settings.BUSINESS_ID = orig_biz_id
        app.dependency_overrides.pop(get_booking_service, None)
        app.dependency_overrides.pop(get_session_factory, None)


def test_admin_login_fail_closed_503_when_rate_limiter_factory_fails(client, db_session):
    """
    Verify fail-closed 503 response and standard error envelope when rate limiter
    session_factory raises an exception during admin login.
    Ensures no authentication cookie or session is created.
    """
    b_id = uuid.uuid4()
    business = Business(
        id=b_id,
        name="Fail Closed Login Biz",
        slug="fc-login-biz",
        email="fc-login@test.com",
        timezone="America/Santiago",
    )

    password_hash = PasswordHash.recommended()
    hashed = password_hash.hash("CorrectPassword123!")
    admin_user = AdminUser(
        id=uuid.uuid4(),
        business_id=b_id,
        email="admin-fc@test.com",
        password_hash=hashed,
        display_name="Admin FC",
        is_active=True,
    )
    db_session.add(business)
    db_session.flush()
    db_session.add(admin_user)
    db_session.commit()

    orig_biz_id = settings.BUSINESS_ID
    settings.BUSINESS_ID = str(business.id)

    def failing_session_factory():
        raise Exception("Database connection dropped on rate limit check")

    app.dependency_overrides[get_session_factory] = lambda: failing_session_factory

    headers = {"Origin": settings.FRONTEND_URL}

    try:
        res = client.post(
            "/api/admin/auth/login",
            json={"email": "admin-fc@test.com", "password": "CorrectPassword123!"},
            headers=headers,
        )
        assert res.status_code == 503, res.text

        # Verify complete standard error envelope
        body = res.json()
        assert "error" in body
        error = body["error"]
        assert error["code"] == "rate_limit_unavailable"
        assert error["message"] == "Servicio de verificación de límites no disponible temporalmente."
        assert "request_id" in error
        assert "details" in error

        # Verify no session cookie set
        assert "booking_admin_session" not in res.cookies

        # Verify no admin session row created in database
        db_session.expire_all()
        session_count = db_session.execute(
            select(func.count(AdminSession.id)).filter(AdminSession.admin_user_id == admin_user.id)
        ).scalar()
        assert session_count == 0

    finally:
        settings.BUSINESS_ID = orig_biz_id
        app.dependency_overrides.pop(get_session_factory, None)
