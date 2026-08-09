import uuid
from datetime import date, time

from sqlalchemy.orm import Session

from app.models.availability import AvailabilityRule
from app.models.business import Business
from app.models.provider import Provider, ProviderService
from app.models.service import Service


def test_inactive_provider_no_slots(db_session: Session):
    # profesional inactivo no genera slots
    b_id = uuid.uuid4()
    b = Business(id=b_id, name="Test Business", slug=f"test-{uuid.uuid4().hex[:8]}", email="test@b.com")
    db_session.add(b)
    db_session.commit()

    # Provider 1 (inactive)
    p_id = uuid.uuid4()
    p = Provider(id=p_id, business_id=b_id, name="Inactive Provider", is_active=False)

    # Service
    s_id = uuid.uuid4()
    s = Service(id=s_id, business_id=b_id, name="Test Service", duration_minutes=60, price_amount=100)

    db_session.add_all([p, s])
    db_session.commit()

    # Link
    ps = ProviderService(business_id=b_id, provider_id=p_id, service_id=s_id)

    # Rule
    rule = AvailabilityRule(
        id=uuid.uuid4(),
        business_id=b_id,
        provider_id=p_id,
        weekday=0,  # Lunes
        start_time=time(9, 0),
        end_time=time(17, 0),
    )
    db_session.add_all([ps, rule])
    db_session.commit()

    # We need to monkeypatch the BUSINESS_ID in settings for the endpoint to pick it up, or just test the service
    from app.services.availability_service import AvailabilityService

    service = AvailabilityService(db_session)
    result = service.get_availability(b_id, s_id, date(2026, 8, 10), None)

    # Inactive provider should not generate slots
    assert len(result["slots"]) == 0


def test_provider_not_offering_service_no_slots(db_session: Session):
    b_id = uuid.uuid4()
    b = Business(id=b_id, name="Test Business 2", slug=f"test-{uuid.uuid4().hex[:8]}", email="test@b.com")
    p_id = uuid.uuid4()
    p = Provider(id=p_id, business_id=b_id, name="Active Provider", is_active=True)
    s_id = uuid.uuid4()
    s = Service(id=s_id, business_id=b_id, name="Test Service 2", duration_minutes=60, price_amount=100)

    # We do NOT create ProviderService link

    rule = AvailabilityRule(
        id=uuid.uuid4(),
        business_id=b_id,
        provider_id=p_id,
        weekday=0,  # Lunes
        start_time=time(9, 0),
        end_time=time(17, 0),
    )

    db_session.add_all([b, p, s, rule])
    db_session.commit()

    from app.services.availability_service import AvailabilityService

    service = AvailabilityService(db_session)
    result = service.get_availability(b_id, s_id, date(2026, 8, 10), None)

    # Provider does not offer service, so no slots
    assert len(result["slots"]) == 0
