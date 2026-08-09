import uuid
from datetime import time

import pytest

from app.models import AvailabilityRule
from app.models.business import Business
from app.models.provider import Provider, ProviderService
from app.models.service import Service


@pytest.fixture(autouse=True)
def seed_test_data(db_session):
    from app.core.config import settings

    b_id = settings.BUSINESS_ID

    business = Business(
        id=b_id,
        name="Test Business",
        slug="test-biz",
        timezone="America/Santiago",
        email="test@b.com",
        minimum_booking_notice_minutes=0,
        booking_horizon_days=60,
        slot_interval_minutes=30,
    )  # noqa: E501
    service = Service(
        id=uuid.UUID("00000000-0000-0000-0000-000000000101"),
        business_id=b_id,
        name="Corte de Cabello",
        duration_minutes=45,
        price_amount=10000,
    )  # noqa: E501
    provider = Provider(
        id=uuid.UUID("00000000-0000-0000-0000-000000000201"), business_id=b_id, name="Juan", email="juan@b.com"
    )  # noqa: E501
    rule = AvailabilityRule(
        id=uuid.uuid4(),
        business_id=b_id,
        provider_id=provider.id,
        weekday=0,  # Lunes
        start_time=time(9, 0),
        end_time=time(18, 0),
    )
    ps = ProviderService(provider_id=provider.id, service_id=service.id, business_id=b_id)

    db_session.add(business)
    db_session.add(service)
    db_session.add(provider)
    db_session.add(rule)
    db_session.add(ps)
    db_session.commit()


def test_get_availability_public(client, db_session):
    from datetime import datetime, timezone

    from app.api.endpoints.availability import get_availability_service
    from app.domain.availability import AvailabilityEngine
    from app.services.availability_service import AvailabilityService

    def mock_now(tz="UTC"):
        return datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)

    def override_get_availability_service():
        return AvailabilityService(db_session, engine=AvailabilityEngine(get_now_fn=mock_now))

    client.app.dependency_overrides[get_availability_service] = override_get_availability_service

    # Use the service_id from the seed script (Corte de Cabello)
    service_id = "00000000-0000-0000-0000-000000000101"
    target_date = "2026-08-10"  # Lunes

    response = client.get(f"/api/public/availability?service_id={service_id}&date={target_date}")

    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "data" in response.json()
    data = response.json()["data"]
    slots = data["slots"]
    assert isinstance(slots, list)

    # Provider 1 has 9:00 - 18:00
    # Service duration 45 mins, interval 30 mins
    # This means slots:
    # 09:00 - 09:45
    # 09:30 - 10:15
    # ... up to 17:00 - 17:45
    # Total slots = (17 - 9) * 2 + 1 = 17 slots
    assert len(slots) == 17

    assert data["timezone"] == "America/Santiago"
    assert data["service_id"] == service_id
    assert data["provider_id"] is None

    # Exact slot check
    assert slots[0]["starts_at"] == "2026-08-10T09:00:00-04:00"
    assert slots[0]["ends_at"] == "2026-08-10T09:45:00-04:00"
    assert "provider_id" not in slots[0]

    assert slots[-1]["starts_at"] == "2026-08-10T17:00:00-04:00"
    assert slots[-1]["ends_at"] == "2026-08-10T17:45:00-04:00"


def test_get_availability_invalid_service(client):
    service_id = "00000000-0000-0000-0000-000000000999"  # Not seeded
    target_date = "2026-08-10"

    response = client.get(f"/api/public/availability?service_id={service_id}&date={target_date}")
    assert response.status_code == 404
    assert "error" in response.json()
    assert "code" in response.json()["error"]
    assert response.json()["error"]["code"] == "service_unavailable"
    assert "Service not found" in response.json()["error"]["message"]


def test_get_availability_validation_error_invalid_uuid(client):
    service_id = "invalid-uuid"
    target_date = "2026-08-10"
    response = client.get(f"/api/public/availability?service_id={service_id}&date={target_date}")
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "validation_error"


def test_get_availability_validation_error_invalid_date(client):
    service_id = "00000000-0000-0000-0000-000000000101"
    target_date = "2026-13-45"
    response = client.get(f"/api/public/availability?service_id={service_id}&date={target_date}")
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "validation_error"


def test_get_availability_validation_error_missing_service(client):
    target_date = "2026-08-10"
    response = client.get(f"/api/public/availability?date={target_date}")
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "validation_error"


def test_get_availability_validation_error_missing_date(client):
    service_id = "00000000-0000-0000-0000-000000000101"
    response = client.get(f"/api/public/availability?service_id={service_id}")
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "validation_error"


def test_get_availability_grouping_two_providers_same_time(client, db_session):
    from datetime import datetime, time, timezone

    from app.api.endpoints.availability import get_availability_service

    # We will use the existing seeded business (b_id) and service (Corte de Cabello)
    from app.core.config import settings
    from app.domain.availability import AvailabilityEngine
    from app.services.availability_service import AvailabilityService

    b_id = settings.BUSINESS_ID
    service_id = "00000000-0000-0000-0000-000000000101"

    # Create Provider 2 (Provider 1 is already seeded)
    provider_2_id = "00000000-0000-0000-0000-000000000202"
    from app.models import AvailabilityRule
    from app.models.provider import Provider, ProviderService

    provider2 = Provider(id=provider_2_id, business_id=b_id, name="Pedro", email="pedro@b.com")
    rule2 = AvailabilityRule(
        id=uuid.uuid4(),
        business_id=b_id,
        provider_id=provider_2_id,
        weekday=0,  # Lunes
        start_time=time(9, 0),
        end_time=time(18, 0),
    )
    ps2 = ProviderService(provider_id=provider_2_id, service_id=service_id, business_id=b_id)

    db_session.add(provider2)
    db_session.add(rule2)
    db_session.add(ps2)
    db_session.commit()

    def mock_now(tz="UTC"):
        return datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)

    def override_get_availability_service():
        return AvailabilityService(db_session, engine=AvailabilityEngine(get_now_fn=mock_now))

    client.app.dependency_overrides[get_availability_service] = override_get_availability_service

    target_date = "2026-08-10"  # Lunes

    # Grouped Request (No provider_id)
    response_grouped = client.get(f"/api/public/availability?service_id={service_id}&date={target_date}")
    assert response_grouped.status_code == 200
    data_grouped = response_grouped.json()["data"]

    assert data_grouped["provider_id"] is None

    slots_grouped = data_grouped["slots"]
    # Even though there are 2 providers working 9 to 18,
    # the 9:00 - 9:45 slot should only appear ONCE.
    assert len(slots_grouped) == 17

    # Only starts_at and ends_at should be exposed
    assert set(slots_grouped[0].keys()) == {"starts_at", "ends_at"}

    assert slots_grouped[0]["starts_at"] == "2026-08-10T09:00:00-04:00"
    assert slots_grouped[0]["ends_at"] == "2026-08-10T09:45:00-04:00"

    # Independent Request (with provider_id)
    response_indep = client.get(
        f"/api/public/availability?service_id={service_id}&date={target_date}&provider_id={provider_2_id}"
    )
    assert response_indep.status_code == 200
    data_indep = response_indep.json()["data"]

    assert data_indep["provider_id"] == str(provider_2_id)

    slots_indep = data_indep["slots"]
    assert len(slots_indep) == 17

    # Only starts_at and ends_at should be exposed, NO provider_id inside the slot
    assert set(slots_indep[0].keys()) == {"starts_at", "ends_at"}
    assert slots_indep[0]["starts_at"] == "2026-08-10T09:00:00-04:00"
    assert slots_indep[0]["ends_at"] == "2026-08-10T09:45:00-04:00"

    client.app.dependency_overrides.clear()
