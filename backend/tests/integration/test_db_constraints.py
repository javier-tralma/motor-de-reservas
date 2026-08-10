import threading
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.booking import Booking, BookingStatus
from app.models.business import Business
from app.models.provider import Provider
from app.models.service import Service


def test_tenant_isolation_fk(db_session: Session):
    # Intentar relacionar un Provider del Business A con un Service del Business B
    b1_id = uuid.uuid4()
    b2_id = uuid.uuid4()

    b1 = Business(id=b1_id, name="B1", slug=f"b1-{uuid.uuid4().hex[:8]}", email="test1@b.com")
    b2 = Business(id=b2_id, name="B2", slug=f"b2-{uuid.uuid4().hex[:8]}", email="test2@b.com")
    db_session.add_all([b1, b2])
    db_session.commit()

    p1 = Provider(id=uuid.uuid4(), business_id=b1_id, name="Provider B1")
    s2 = Service(id=uuid.uuid4(), business_id=b2_id, name="Service B2", duration_minutes=30, price_amount=100)
    db_session.add_all([p1, s2])
    db_session.commit()

    # Esto debería fallar debido a que ProviderService tiene FK compuesta (business_id, provider_id)
    # y si intentamos mezclar, violaría la constraint.
    # ProviderService usa business_id, provider_id y service_id.
    from app.models.provider import ProviderService

    ps = ProviderService(business_id=b1_id, provider_id=p1.id, service_id=s2.id)
    db_session.add(ps)
    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_overlapping_bookings_gist(db_session: Session):
    # Test GiST exclusion constraint on Bookings
    b_id = uuid.uuid4()
    b = Business(id=b_id, name="B GiST", slug=f"b-gist-{uuid.uuid4().hex[:8]}", email="gist@b.com")
    db_session.add(b)
    db_session.commit()

    p_id = uuid.uuid4()
    p = Provider(id=p_id, business_id=b_id, name="P GiST")
    db_session.add(p)
    db_session.commit()

    # Crear primera reserva
    now = datetime.now(timezone.utc)
    start_time = now
    end_time = now + timedelta(minutes=60)

    s_id = uuid.uuid4()
    s = Service(id=s_id, business_id=b_id, name="S", duration_minutes=60, price_amount=0)
    db_session.add(s)
    db_session.commit()

    from app.models.booking import BookingSource, EmailDeliveryStatus

    b1 = Booking(
        id=uuid.uuid4(),
        business_id=b_id,
        provider_id=p_id,
        service_id=s_id,
        public_reference=uuid.uuid4().hex,
        client_request_id=uuid.uuid4(),
        customer_name="Test",
        customer_email="test@test.com",
        customer_phone="123456789",
        starts_at=start_time,
        ends_at=end_time,
        status=BookingStatus.confirmed,
        source=BookingSource.public,
        service_name_snapshot="S",
        duration_minutes_snapshot=60,
        price_amount_snapshot=0,
        provider_name_snapshot="P GiST",
        email_delivery_status=EmailDeliveryStatus.not_requested,
    )
    db_session.add(b1)
    db_session.commit()

    # Intentar solapar parcialmente (falla exclusión GIST)
    b2 = Booking(
        id=uuid.uuid4(),
        business_id=b_id,
        provider_id=p_id,
        service_id=s_id,
        public_reference=uuid.uuid4().hex,
        client_request_id=uuid.uuid4(),
        customer_name="Test 2",
        customer_email="test2@test.com",
        customer_phone="123456789",
        starts_at=start_time + timedelta(minutes=30),
        ends_at=end_time + timedelta(minutes=30),
        status=BookingStatus.confirmed,
        source=BookingSource.public,
        service_name_snapshot="S",
        duration_minutes_snapshot=60,
        price_amount_snapshot=0,
        provider_name_snapshot="P GiST",
        email_delivery_status=EmailDeliveryStatus.not_requested,
    )
    db_session.add(b2)
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()

    assert "exclusion" in str(exc_info.value).lower()
    db_session.rollback()

    # Si cancelo b1, b2 debería poder insertarse
    b1_reload = db_session.get(Booking, b1.id)
    b1_reload.status = BookingStatus.cancelled
    db_session.commit()

    b2_retry = Booking(
        id=uuid.uuid4(),
        business_id=b_id,
        provider_id=p_id,
        service_id=s_id,
        public_reference=uuid.uuid4().hex,
        client_request_id=uuid.uuid4(),
        customer_name="Test 2",
        customer_email="test2@test.com",
        customer_phone="123456789",
        starts_at=start_time + timedelta(minutes=30),
        ends_at=end_time + timedelta(minutes=30),
        status=BookingStatus.confirmed,
        source=BookingSource.public,
        service_name_snapshot="S",
        duration_minutes_snapshot=60,
        price_amount_snapshot=0,
        provider_name_snapshot="P GiST",
        email_delivery_status=EmailDeliveryStatus.not_requested,
    )
    db_session.add(b2_retry)
    db_session.commit()  # Should succeed now


def test_concurrent_booking_exclusion():
    # prepara negocio, servicio y profesional
    b_id = uuid.uuid4()
    p_id = uuid.uuid4()
    s_id = uuid.uuid4()

    db_setup = SessionLocal()
    try:
        b = Business(id=b_id, name="B Conc", slug=f"b-conc-{uuid.uuid4().hex[:8]}", email="conc@b.com")
        p = Provider(id=p_id, business_id=b_id, name="P Conc")
        s = Service(id=s_id, business_id=b_id, name="S Conc", duration_minutes=60, price_amount=0)
        db_setup.add_all([b, p, s])
        db_setup.commit()
    finally:
        db_setup.close()

    barrier = threading.Barrier(2, timeout=5)
    results = []

    def worker():
        session = SessionLocal()
        try:
            import psycopg

            from app.models.booking import BookingSource, EmailDeliveryStatus

            start_time = datetime(2026, 8, 10, 10, 0, tzinfo=timezone.utc)

            b_new = Booking(
                id=uuid.uuid4(),
                business_id=b_id,
                provider_id=p_id,
                service_id=s_id,
                public_reference=uuid.uuid4().hex,
                client_request_id=uuid.uuid4(),
                customer_name="Conc Test",
                customer_email="conc@test.com",
                customer_phone="123",
                starts_at=start_time,
                ends_at=start_time + timedelta(minutes=60),
                status=BookingStatus.confirmed,
                source=BookingSource.public,
                service_name_snapshot="S",
                duration_minutes_snapshot=60,
                price_amount_snapshot=0,
                provider_name_snapshot="P",
                email_delivery_status=EmailDeliveryStatus.not_requested,
            )
            barrier.wait(timeout=5)
            from sqlalchemy import select

            session.execute(select(Provider).filter_by(id=p_id).with_for_update())
            session.add(b_new)
            session.commit()
            results.append("success")
        except IntegrityError as e:
            session.rollback()
            if (
                hasattr(e, "orig")
                and hasattr(psycopg, "errors")
                and isinstance(e.orig, psycopg.errors.ExclusionViolation)
            ):
                if e.orig.diag.constraint_name == "bookings_provider_no_overlap":
                    results.append("exclusion")
                else:
                    results.append(f"wrong_constraint: {e.orig.diag.constraint_name}")
            else:
                results.append(f"other_integrity_error: {e}")
        except Exception as e:
            session.rollback()
            results.append(f"exception: {e}")
        finally:
            session.close()

    try:
        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)

        t1.start()
        t2.start()

        t1.join(timeout=5)
        t2.join(timeout=5)

        assert not t1.is_alive(), "Thread 1 did not finish"
        assert not t2.is_alive(), "Thread 2 did not finish"

        assert results.count("success") == 1
        assert results.count("exclusion") == 1

    finally:
        # limpia los datos
        db_clean = SessionLocal()
        try:
            db_clean.query(Booking).filter(Booking.business_id == b_id).delete()
            db_clean.query(Service).filter(Service.business_id == b_id).delete()
            db_clean.query(Provider).filter(Provider.business_id == b_id).delete()
            db_clean.query(Business).filter(Business.id == b_id).delete()
            db_clean.commit()
        finally:
            db_clean.close()
