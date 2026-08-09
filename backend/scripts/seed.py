import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import time

from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.availability import AvailabilityRule
from app.models.business import Business
from app.models.provider import Provider, ProviderService
from app.models.service import Service

engine = create_engine(settings.DATABASE_URL)


def run_seed():
    with Session(engine) as session:
        business_id = settings.BUSINESS_ID

        # 1. Business
        stmt = (
            insert(Business)
            .values(
                id=business_id,
                name="Estudio Nómada",
                slug="estudio-nomada",
                timezone="America/Santiago",
                locale="es-CL",
                currency="CLP",
                email="hola@estudionomada.cl",
                minimum_booking_notice_minutes=120,
                booking_horizon_days=60,
                slot_interval_minutes=15,
            )
            .on_conflict_do_update(index_elements=["id"], set_={"name": "Estudio Nómada", "slug": "estudio-nomada"})
        )
        session.execute(stmt)

        # 2. Services
        service_1_id = "00000000-0000-0000-0000-000000000101"
        stmt = (
            insert(Service)
            .values(
                id=service_1_id,
                business_id=business_id,
                name="Corte de Cabello",
                duration_minutes=45,
                price_amount=15000,
                is_active=True,
                sort_order=1,
            )  # noqa: E501
            .on_conflict_do_update(
                index_elements=["id"], set_={"name": "Corte de Cabello", "duration_minutes": 45, "price_amount": 15000}
            )  # noqa: E501
        )
        session.execute(stmt)

        service_2_id = "00000000-0000-0000-0000-000000000102"
        stmt = (
            insert(Service)
            .values(
                id=service_2_id,
                business_id=business_id,
                name="Barba Spa",
                duration_minutes=30,
                price_amount=10000,
                is_active=True,
                sort_order=2,
            )  # noqa: E501
            .on_conflict_do_update(
                index_elements=["id"], set_={"name": "Barba Spa", "duration_minutes": 30, "price_amount": 10000}
            )  # noqa: E501
        )
        session.execute(stmt)

        # 3. Providers
        provider_1_id = "00000000-0000-0000-0000-000000000201"
        stmt = (
            insert(Provider)
            .values(id=provider_1_id, business_id=business_id, name="Camila Rojas", is_active=True, sort_order=1)
            .on_conflict_do_update(index_elements=["id"], set_={"name": "Camila Rojas"})
        )
        session.execute(stmt)

        provider_2_id = "00000000-0000-0000-0000-000000000202"
        stmt = (
            insert(Provider)
            .values(id=provider_2_id, business_id=business_id, name="Javier Pérez", is_active=True, sort_order=2)
            .on_conflict_do_update(index_elements=["id"], set_={"name": "Javier Pérez"})
        )
        session.execute(stmt)

        # 4. Provider Services
        stmt = (
            insert(ProviderService)
            .values(
                [
                    {"business_id": business_id, "provider_id": provider_1_id, "service_id": service_1_id},
                    {"business_id": business_id, "provider_id": provider_2_id, "service_id": service_1_id},
                    {"business_id": business_id, "provider_id": provider_2_id, "service_id": service_2_id},
                ]
            )
            .on_conflict_do_nothing(index_elements=["provider_id", "service_id"])
        )
        session.execute(stmt)

        # 5. Availability Rules
        rules = [
            {
                "id": "00000000-0000-0000-0000-000000000301",
                "business_id": business_id,
                "provider_id": provider_1_id,
                "weekday": 0,
                "start_time": time(9, 0),
                "end_time": time(14, 0),
            },  # noqa: E501
            {
                "id": "00000000-0000-0000-0000-000000000302",
                "business_id": business_id,
                "provider_id": provider_1_id,
                "weekday": 0,
                "start_time": time(15, 0),
                "end_time": time(18, 0),
            },  # noqa: E501
            {
                "id": "00000000-0000-0000-0000-000000000303",
                "business_id": business_id,
                "provider_id": provider_2_id,
                "weekday": 0,
                "start_time": time(10, 0),
                "end_time": time(19, 0),
            },  # noqa: E501
        ]

        for rule in rules:
            stmt = (
                insert(AvailabilityRule)
                .values(rule)
                .on_conflict_do_update(
                    index_elements=["id"],
                    set_={"start_time": rule["start_time"], "end_time": rule["end_time"], "weekday": rule["weekday"]},
                )  # noqa: E501
            )
            session.execute(stmt)

        session.commit()
        print("Seed data successfully inserted.")


if __name__ == "__main__":
    run_seed()
