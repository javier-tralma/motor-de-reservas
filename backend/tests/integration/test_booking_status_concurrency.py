import threading
import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy.orm import sessionmaker

from app.api.endpoints.availability import DomainError
from app.core.config import settings
from app.domain.availability import AvailabilityEngine
from app.integrations.email.service import FakeEmailService
from app.models.availability import AvailabilityRule
from app.models.booking import Booking, BookingSource, BookingStatus, EmailDeliveryStatus
from app.models.business import Business
from app.models.provider import Provider, ProviderService
from app.models.service import Service
from app.services.availability_service import AvailabilityService
from app.services.booking_service import BookingService
from tests.conftest import engine as db_engine


def setup_concurrency_booking_data(session):
    biz_id = uuid.uuid4()
    settings.BUSINESS_ID = str(biz_id)

    biz = Business(
        id=biz_id,
        name="Estudio Concurrencia",
        slug=f"estudio-conc-{uuid.uuid4().hex[:6]}",
        timezone="America/Santiago",
        locale="es-CL",
        email="conc@estudionomada.cl",
    )
    session.add(biz)
    session.commit()

    service = Service(
        id=uuid.uuid4(),
        business_id=biz_id,
        name="Corte Concurrente",
        duration_minutes=30,
        price_amount=15000,
        is_active=True,
    )
    session.add(service)

    provider = Provider(
        id=uuid.uuid4(),
        business_id=biz_id,
        name="Camila Concurrente",
        is_active=True,
    )
    session.add(provider)
    session.commit()

    # Link provider to service and add weekly availability rule for Monday (weekday 0)
    ps = ProviderService(business_id=biz_id, provider_id=provider.id, service_id=service.id)
    rule = AvailabilityRule(
        id=uuid.uuid4(),
        business_id=biz_id,
        provider_id=provider.id,
        weekday=0,  # Monday
        start_time=time(9, 0),
        end_time=time(18, 0),
    )
    session.add_all([ps, rule])
    session.commit()

    # Create a booking on Monday 2026-08-10 at 10:00 local (14:00 UTC)
    booking = Booking(
        id=uuid.uuid4(),
        business_id=biz_id,
        service_id=service.id,
        provider_id=provider.id,
        public_reference=f"REF_{uuid.uuid4().hex[:10]}",
        customer_name="Cliente Concurrente",
        customer_email="conc@test.cl",
        customer_phone="+56912345678",
        customer_notes="",
        starts_at=datetime(2026, 8, 10, 14, 0, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 8, 10, 14, 30, 0, tzinfo=timezone.utc),
        status=BookingStatus.confirmed,
        source=BookingSource.public,
        service_name_snapshot=service.name,
        duration_minutes_snapshot=30,
        price_amount_snapshot=15000,
        provider_name_snapshot=provider.name,
        email_delivery_status=EmailDeliveryStatus.not_requested,
    )
    session.add(booking)
    session.commit()

    return biz, service, provider, booking


def cleanup_business_data(session, business_id: uuid.UUID):
    try:
        session.query(Booking).filter_by(business_id=business_id).delete()
        session.query(AvailabilityRule).filter_by(business_id=business_id).delete()
        session.query(ProviderService).filter_by(business_id=business_id).delete()
        session.query(Provider).filter_by(business_id=business_id).delete()
        session.query(Service).filter_by(business_id=business_id).delete()
        session.query(Business).filter_by(id=business_id).delete()
        session.commit()
    except Exception:
        session.rollback()


def test_concurrent_status_updates_with_barrier():
    SessionMaker = sessionmaker(bind=db_engine)
    setup_session = SessionMaker()

    biz_id = None
    try:
        biz, service, provider, booking = setup_concurrency_booking_data(setup_session)
        biz_id = biz.id
        booking_id = booking.id
        fixed_now = datetime(2026, 8, 10, 12, 0, 0, tzinfo=timezone.utc)

        barrier = threading.Barrier(2, timeout=5.0)
        results = [None, None]
        exceptions = [None, None]

        def worker(thread_idx, new_status):
            session = SessionMaker()
            try:
                avail_svc = AvailabilityService(session)
                email_svc = FakeEmailService()
                booking_svc = BookingService(session, avail_svc, email_svc)

                # Wait at barrier immediately BEFORE attempting to call service / obtain FOR UPDATE lock
                barrier.wait()

                res = booking_svc.update_booking_status(
                    business_id=biz_id,
                    booking_id=booking_id,
                    new_status=new_status,
                    now=fixed_now,
                )
                results[thread_idx] = res
            except Exception as e:
                exceptions[thread_idx] = e
            finally:
                session.close()

        t1 = threading.Thread(target=worker, args=(0, BookingStatus.completed))
        t2 = threading.Thread(target=worker, args=(1, BookingStatus.cancelled))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Exactly one thread succeeds and the other receives DomainError(409 invalid_status_transition)
        successes = [r for r in results if r is not None]
        errs = [e for e in exceptions if e is not None]

        assert len(successes) == 1, f"Expected 1 success, got {len(successes)}"
        assert len(errs) == 1, f"Expected 1 error, got {len(errs)}"

        error = errs[0]
        assert isinstance(error, DomainError)
        assert error.status_code == 409
        assert error.code == "invalid_status_transition"
    finally:
        if biz_id:
            cleanup_session = SessionMaker()
            try:
                cleanup_business_data(cleanup_session, biz_id)
            finally:
                cleanup_session.close()
        setup_session.close()


def test_status_change_effects_on_public_availability(db_session):
    biz, service, provider, booking = setup_concurrency_booking_data(db_session)
    biz_id = biz.id
    booking_id = booking.id

    try:
        now = datetime(2026, 8, 10, 8, 0, 0, tzinfo=timezone.utc)
        engine_mock = AvailabilityEngine(get_now_fn=lambda *args, **kwargs: now)

        avail_svc = AvailabilityService(db_session, engine=engine_mock)
        email_svc = FakeEmailService()
        booking_svc = BookingService(db_session, avail_svc, email_svc)
        target_date = date(2026, 8, 10)

        # 1. Initially, slot 10:00 local (14:00 UTC) is occupied (confirmed booking)
        res_initial = avail_svc.get_availability(biz_id, service.id, target_date, provider.id)
        slot_starts = [s.starts_at for s in res_initial["slots"]]
        booked_start = datetime(2026, 8, 10, 14, 0, 0, tzinfo=timezone.utc)
        assert booked_start not in slot_starts, "Slot at 10:00 local should be occupied when confirmed"

        # 2. Transition to completed -> slot MUST REMAIN occupied
        booking_svc.update_booking_status(biz_id, booking_id, BookingStatus.completed, now)

        res_completed = avail_svc.get_availability(biz_id, service.id, target_date, provider.id)
        slot_starts_completed = [s.starts_at for s in res_completed["slots"]]
        assert booked_start not in slot_starts_completed, "Slot at 10:00 local must remain occupied when completed"

        # 3. Create another booking to test cancelled status freeing availability
        booking2 = Booking(
            id=uuid.uuid4(),
            business_id=biz_id,
            service_id=service.id,
            provider_id=provider.id,
            public_reference=f"REF_{uuid.uuid4().hex[:10]}",
            customer_name="Cliente 2",
            customer_email="c2@test.cl",
            customer_phone="+56912345678",
            customer_notes="",
            starts_at=datetime(2026, 8, 10, 15, 0, 0, tzinfo=timezone.utc),  # 11:00 local Santiago
            ends_at=datetime(2026, 8, 10, 15, 30, 0, tzinfo=timezone.utc),
            status=BookingStatus.confirmed,
            source=BookingSource.public,
            service_name_snapshot=service.name,
            duration_minutes_snapshot=30,
            price_amount_snapshot=15000,
            provider_name_snapshot=provider.name,
            email_delivery_status=EmailDeliveryStatus.not_requested,
        )
        db_session.add(booking2)
        db_session.commit()

        booked2_start = datetime(2026, 8, 10, 15, 0, 0, tzinfo=timezone.utc)
        res_b2_before = avail_svc.get_availability(biz_id, service.id, target_date, provider.id)
        assert booked2_start not in [s.starts_at for s in res_b2_before["slots"]]

        # Transition booking2 to cancelled -> slot MUST BE FREED and appear in public availability
        booking_svc.update_booking_status(biz_id, booking2.id, BookingStatus.cancelled, now)

        res_b2_cancelled = avail_svc.get_availability(biz_id, service.id, target_date, provider.id)
        assert booked2_start in [s.starts_at for s in res_b2_cancelled["slots"]], "Cancelled slot must be freed"
    finally:
        cleanup_business_data(db_session, biz_id)
