import threading
import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.api.endpoints.availability import DomainError
from app.core.db import SessionLocal
from app.integrations.email.service import FakeEmailService
from app.models.availability import AvailabilityRule
from app.models.booking import Booking
from app.models.business import Business
from app.models.provider import Provider, ProviderService
from app.models.service import Service
from app.schemas.booking import BookingCreateRequest
from app.services.availability_service import AvailabilityService
from app.services.booking_service import BookingService


def test_concurrent_booking_exclusion():
    b_id = uuid.uuid4()
    p_id = uuid.uuid4()
    s_id = uuid.uuid4()
    target_date = date(2026, 8, 10)

    db_setup = SessionLocal()
    try:
        business = Business(id=b_id, name="Test B", slug=f"test-b-conc-{uuid.uuid4().hex[:8]}", email="test@b.com")
        provider = Provider(id=p_id, business_id=b_id, name="Test P")
        service = Service(id=s_id, business_id=b_id, name="Test S", duration_minutes=45, price_amount=100)
        ps = ProviderService(business_id=b_id, provider_id=p_id, service_id=s_id)
        rule = AvailabilityRule(
            id=uuid.uuid4(),
            business_id=b_id,
            provider_id=p_id,
            weekday=target_date.weekday(),
            start_time=datetime.strptime("09:00", "%H:%M").time(),
            end_time=datetime.strptime("18:00", "%H:%M").time(),
        )
        db_setup.add_all([business, provider, service, ps, rule])
        db_setup.commit()
        b_timezone = business.timezone
    finally:
        db_setup.close()

    try:
        local_tz = ZoneInfo(b_timezone)
        starts_at = datetime.combine(target_date, datetime.strptime("09:00", "%H:%M").time(), tzinfo=local_tz)

        barrier = threading.Barrier(2, timeout=5.0)
        results = [None, None]

        def book_slot(thread_idx):
            db_session = SessionLocal()
            try:
                from datetime import timezone

                from app.domain.availability import AvailabilityEngine

                engine = AvailabilityEngine(get_now_fn=lambda tz="UTC": datetime(2026, 8, 1, tzinfo=timezone.utc))
                availability_service = AvailabilityService(db_session, engine=engine)

                email_service = FakeEmailService()
                booking_service = BookingService(db_session, availability_service, email_service)

                request = BookingCreateRequest(
                    service_id=s_id,
                    provider_id=p_id,
                    starts_at=starts_at,
                    client_request_id=uuid.uuid4(),
                    customer_name=f"Thread {thread_idx}",
                    customer_email=f"thread{thread_idx}@example.com",
                    customer_phone="+56900000000",
                )

                barrier.wait()
                booking_service.create_public_booking(b_id, request)
                results[thread_idx] = "SUCCESS"
            except DomainError as e:
                if e.code == "slot_unavailable":
                    results[thread_idx] = "CONFLICT"
                else:
                    results[thread_idx] = f"ERROR: {e.code}"
            except Exception as e:
                results[thread_idx] = f"EXCEPTION: {getattr(e, 'code', type(e).__name__)}"
            finally:
                db_session.close()

        t1 = threading.Thread(target=book_slot, args=(0,))
        t2 = threading.Thread(target=book_slot, args=(1,))
        t1.start()
        t2.start()
        t1.join(timeout=5.0)
        t2.join(timeout=5.0)
        assert not t1.is_alive()
        assert not t2.is_alive()

        assert "SUCCESS" in results
        assert "CONFLICT" in results
    finally:
        db_cleanup = SessionLocal()
        try:
            db_cleanup.query(Booking).filter(Booking.business_id == b_id).delete()
            db_cleanup.query(AvailabilityRule).filter(AvailabilityRule.business_id == b_id).delete()
            db_cleanup.query(ProviderService).filter(ProviderService.business_id == b_id).delete()
            db_cleanup.query(Service).filter(Service.business_id == b_id).delete()
            db_cleanup.query(Provider).filter(Provider.business_id == b_id).delete()
            db_cleanup.query(Business).filter(Business.id == b_id).delete()
            db_cleanup.commit()
        finally:
            db_cleanup.close()


def test_concurrent_idempotency_replay():
    b_id = uuid.uuid4()
    p_id = uuid.uuid4()
    s_id = uuid.uuid4()
    target_date = date(2026, 8, 10)

    db_setup = SessionLocal()
    try:
        business = Business(id=b_id, name="Test B", slug=f"test-b-idem-{uuid.uuid4().hex[:8]}", email="test@b.com")
        provider = Provider(id=p_id, business_id=b_id, name="Test P")
        service = Service(id=s_id, business_id=b_id, name="Test S", duration_minutes=45, price_amount=100)
        ps = ProviderService(business_id=b_id, provider_id=p_id, service_id=s_id)
        rule = AvailabilityRule(
            id=uuid.uuid4(),
            business_id=b_id,
            provider_id=p_id,
            weekday=target_date.weekday(),
            start_time=datetime.strptime("09:00", "%H:%M").time(),
            end_time=datetime.strptime("18:00", "%H:%M").time(),
        )
        db_setup.add_all([business, provider, service, ps, rule])
        db_setup.commit()
        b_timezone = business.timezone
    finally:
        db_setup.close()

    try:
        local_tz = ZoneInfo(b_timezone)
        starts_at = datetime.combine(target_date, datetime.strptime("09:00", "%H:%M").time(), tzinfo=local_tz)

        barrier = threading.Barrier(2, timeout=5.0)
        results = [None, None]
        client_req_id = uuid.uuid4()

        def book_slot(thread_idx):
            db_session = SessionLocal()
            try:
                from datetime import timezone

                from app.domain.availability import AvailabilityEngine

                engine = AvailabilityEngine(get_now_fn=lambda tz="UTC": datetime(2026, 8, 1, tzinfo=timezone.utc))
                availability_service = AvailabilityService(db_session, engine=engine)

                email_service = FakeEmailService()
                booking_service = BookingService(db_session, availability_service, email_service)

                request = BookingCreateRequest(
                    service_id=s_id,
                    provider_id=p_id,
                    starts_at=starts_at,
                    client_request_id=client_req_id,
                    customer_name="Idempotency User",
                    customer_email="idem@example.com",
                    customer_phone="+56900000000",
                )

                barrier.wait()
                _, created = booking_service.create_public_booking(b_id, request)
                if created:
                    results[thread_idx] = "CREATED"
                else:
                    results[thread_idx] = "REPLAYED"

                if created:
                    assert len(email_service.sent_emails) == 1
                else:
                    assert len(email_service.sent_emails) == 0
            except Exception as e:
                results[thread_idx] = f"EXCEPTION: {getattr(e, 'code', type(e).__name__)}"
            finally:
                db_session.close()

        t1 = threading.Thread(target=book_slot, args=(0,))
        t2 = threading.Thread(target=book_slot, args=(1,))
        t1.start()
        t2.start()
        t1.join(timeout=5.0)
        t2.join(timeout=5.0)
        assert not t1.is_alive()
        assert not t2.is_alive()

        assert "CREATED" in results
        assert "REPLAYED" in results

        db_verify = SessionLocal()
        try:
            bookings = db_verify.execute(select(Booking).filter_by(business_id=b_id)).scalars().all()
            assert len(bookings) == 1
        finally:
            db_verify.close()
    finally:
        db_cleanup = SessionLocal()
        try:
            db_cleanup.query(Booking).filter(Booking.business_id == b_id).delete()
            db_cleanup.query(AvailabilityRule).filter(AvailabilityRule.business_id == b_id).delete()
            db_cleanup.query(ProviderService).filter(ProviderService.business_id == b_id).delete()
            db_cleanup.query(Service).filter(Service.business_id == b_id).delete()
            db_cleanup.query(Provider).filter(Provider.business_id == b_id).delete()
            db_cleanup.query(Business).filter(Business.id == b_id).delete()
            db_cleanup.commit()
        finally:
            db_cleanup.close()


def test_concurrent_idempotency_conflict():
    b_id = uuid.uuid4()
    p_id = uuid.uuid4()
    s_id = uuid.uuid4()
    target_date = date(2026, 8, 10)

    db_setup = SessionLocal()
    try:
        business = Business(id=b_id, name="Test B", slug=f"test-b-conf-{uuid.uuid4().hex[:8]}", email="test@b.com")
        provider = Provider(id=p_id, business_id=b_id, name="Test P")
        service = Service(id=s_id, business_id=b_id, name="Test S", duration_minutes=45, price_amount=100)
        ps = ProviderService(business_id=b_id, provider_id=p_id, service_id=s_id)
        rule = AvailabilityRule(
            id=uuid.uuid4(),
            business_id=b_id,
            provider_id=p_id,
            weekday=target_date.weekday(),
            start_time=datetime.strptime("09:00", "%H:%M").time(),
            end_time=datetime.strptime("18:00", "%H:%M").time(),
        )
        db_setup.add_all([business, provider, service, ps, rule])
        db_setup.commit()
        b_timezone = business.timezone
    finally:
        db_setup.close()

    try:
        local_tz = ZoneInfo(b_timezone)
        starts_at = datetime.combine(target_date, datetime.strptime("09:00", "%H:%M").time(), tzinfo=local_tz)

        barrier = threading.Barrier(2, timeout=5.0)
        results = [None, None]
        client_req_id = uuid.uuid4()

        def book_slot(thread_idx):
            db_session = SessionLocal()
            try:
                from datetime import timezone

                from app.domain.availability import AvailabilityEngine

                engine = AvailabilityEngine(get_now_fn=lambda tz="UTC": datetime(2026, 8, 1, tzinfo=timezone.utc))
                availability_service = AvailabilityService(db_session, engine=engine)

                email_service = FakeEmailService()
                booking_service = BookingService(db_session, availability_service, email_service)

                request = BookingCreateRequest(
                    service_id=s_id,
                    provider_id=p_id,
                    starts_at=starts_at,
                    client_request_id=client_req_id,
                    customer_name=f"Idempotency User {thread_idx}",
                    customer_email="idem@example.com",
                    customer_phone="+56900000000",
                )

                barrier.wait()
                _, created = booking_service.create_public_booking(b_id, request)
                if created:
                    results[thread_idx] = "CREATED"
                else:
                    results[thread_idx] = "REPLAYED"

                if created:
                    assert len(email_service.sent_emails) == 1
                else:
                    assert len(email_service.sent_emails) == 0
            except Exception as e:
                results[thread_idx] = f"EXCEPTION: {getattr(e, 'code', type(e).__name__)}"
            finally:
                db_session.close()

        t1 = threading.Thread(target=book_slot, args=(0,))
        t2 = threading.Thread(target=book_slot, args=(1,))
        t1.start()
        t2.start()
        t1.join(timeout=5.0)
        t2.join(timeout=5.0)
        assert not t1.is_alive()
        assert not t2.is_alive()

        assert "CREATED" in results
        assert "EXCEPTION: idempotency_conflict" in results

        db_verify = SessionLocal()
        try:
            bookings = db_verify.execute(select(Booking).filter_by(business_id=b_id)).scalars().all()
            assert len(bookings) == 1
        finally:
            db_verify.close()
    finally:
        db_cleanup = SessionLocal()
        try:
            db_cleanup.query(Booking).filter(Booking.business_id == b_id).delete()
            db_cleanup.query(AvailabilityRule).filter(AvailabilityRule.business_id == b_id).delete()
            db_cleanup.query(ProviderService).filter(ProviderService.business_id == b_id).delete()
            db_cleanup.query(Service).filter(Service.business_id == b_id).delete()
            db_cleanup.query(Provider).filter(Provider.business_id == b_id).delete()
            db_cleanup.query(Business).filter(Business.id == b_id).delete()
            db_cleanup.commit()
        finally:
            db_cleanup.close()


def test_any_provider_fallback_on_concurrency():
    b_id = uuid.uuid4()
    p1_id, p2_id = sorted([uuid.uuid4(), uuid.uuid4()])
    s_id = uuid.uuid4()
    target_date = date(2026, 8, 10)

    db_setup = SessionLocal()
    try:
        business = Business(id=b_id, name="Test B", slug=f"test-b-any-{uuid.uuid4().hex[:8]}", email="test@b.com")
        p1 = Provider(id=p1_id, business_id=b_id, name="Provider 1")
        p2 = Provider(id=p2_id, business_id=b_id, name="Provider 2")
        service = Service(id=s_id, business_id=b_id, name="Test S", duration_minutes=45, price_amount=100)
        ps1 = ProviderService(business_id=b_id, provider_id=p1_id, service_id=s_id)
        ps2 = ProviderService(business_id=b_id, provider_id=p2_id, service_id=s_id)
        r1 = AvailabilityRule(
            id=uuid.uuid4(),
            business_id=b_id,
            provider_id=p1_id,
            weekday=target_date.weekday(),
            start_time=datetime.strptime("09:00", "%H:%M").time(),
            end_time=datetime.strptime("18:00", "%H:%M").time(),
        )
        r2 = AvailabilityRule(
            id=uuid.uuid4(),
            business_id=b_id,
            provider_id=p2_id,
            weekday=target_date.weekday(),
            start_time=datetime.strptime("09:00", "%H:%M").time(),
            end_time=datetime.strptime("18:00", "%H:%M").time(),
        )
        db_setup.add_all([business, p1, p2, service, ps1, ps2, r1, r2])
        db_setup.commit()
        b_timezone = business.timezone
        service_duration = service.duration_minutes
    finally:
        db_setup.close()

    db_session = None
    try:
        local_tz = ZoneInfo(b_timezone)
        starts_at = datetime.combine(target_date, datetime.strptime("09:00", "%H:%M").time(), tzinfo=local_tz)

        def occupy_p1_concurrently():
            db_occ = SessionLocal()
            try:
                from app.models.booking import Booking, BookingSource, BookingStatus, EmailDeliveryStatus

                occ = Booking(
                    business_id=b_id,
                    service_id=s_id,
                    provider_id=p1_id,
                    public_reference="occp1",
                    client_request_id=uuid.uuid4(),
                    request_fingerprint="f",
                    customer_name="Occ",
                    customer_email="o@e.com",
                    customer_phone="1",
                    starts_at=starts_at,
                    ends_at=starts_at + timedelta(minutes=service_duration),
                    status=BookingStatus.confirmed,
                    source=BookingSource.public,
                    service_name_snapshot="S",
                    duration_minutes_snapshot=45,
                    price_amount_snapshot=100,
                    provider_name_snapshot="P1",
                    email_delivery_status=EmailDeliveryStatus.not_requested,
                )
                db_occ.add(occ)
                db_occ.commit()
            finally:
                db_occ.close()

        db_session = SessionLocal()
        from datetime import timezone

        from app.domain.availability import AvailabilityEngine

        engine = AvailabilityEngine(get_now_fn=lambda tz="UTC": datetime(2026, 8, 1, tzinfo=timezone.utc))
        availability_service = AvailabilityService(db_session, engine=engine)

        original_get = availability_service.get_availability

        def mock_get(*args, **kwargs):
            res = original_get(*args, **kwargs)
            occupy_p1_concurrently()
            return res

        availability_service.get_availability = mock_get

        email_service = FakeEmailService()
        booking_service = BookingService(db_session, availability_service, email_service)

        request = BookingCreateRequest(
            service_id=s_id,
            provider_id=None,
            starts_at=starts_at,
            client_request_id=uuid.uuid4(),
            customer_name="Any User",
            customer_email="any@example.com",
            customer_phone="+56900000000",
        )

        b, created = booking_service.create_public_booking(b_id, request)
        assert created is True
        assert b.provider_id == p2_id

    finally:
        if db_session:
            db_session.close()
        db_cleanup = SessionLocal()
        try:
            db_cleanup.query(Booking).filter(Booking.business_id == b_id).delete()
            db_cleanup.query(AvailabilityRule).filter(AvailabilityRule.business_id == b_id).delete()
            db_cleanup.query(ProviderService).filter(ProviderService.business_id == b_id).delete()
            db_cleanup.query(Service).filter(Service.business_id == b_id).delete()
            db_cleanup.query(Provider).filter(Provider.business_id == b_id).delete()
            db_cleanup.query(Business).filter(Business.id == b_id).delete()
            db_cleanup.commit()
        finally:
            db_cleanup.close()
