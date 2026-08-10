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
                phone="+56912345678",
                address="Calle Valparaíso 123, Viña del Mar",
                minimum_booking_notice_minutes=120,
                booking_horizon_days=60,
                slot_interval_minutes=15,
            )
            .on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "name": "Estudio Nómada",
                    "slug": "estudio-nomada",
                    "email": "hola@estudionomada.cl",
                    "phone": "+56912345678",
                    "address": "Calle Valparaíso 123, Viña del Mar",
                },
            )
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
                description="Corte personalizado con asesoría de estilo, lavado y peinado.",
                duration_minutes=45,
                price_amount=15000,
                is_active=True,
                sort_order=1,
            )
            .on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "name": "Corte de Cabello",
                    "description": "Corte personalizado con asesoría de estilo, lavado y peinado.",
                    "duration_minutes": 45,
                    "price_amount": 15000,
                },
            )
        )
        session.execute(stmt)

        service_2_id = "00000000-0000-0000-0000-000000000102"
        stmt = (
            insert(Service)
            .values(
                id=service_2_id,
                business_id=business_id,
                name="Barba Spa",
                description="Perfilado de barba con toallas calientes y aceites hidratantes.",
                duration_minutes=30,
                price_amount=10000,
                is_active=True,
                sort_order=2,
            )
            .on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "name": "Barba Spa",
                    "description": "Perfilado de barba con toallas calientes y aceites hidratantes.",
                    "duration_minutes": 30,
                    "price_amount": 10000,
                },
            )
        )
        session.execute(stmt)

        # 3. Providers
        provider_1_id = "00000000-0000-0000-0000-000000000201"
        stmt = (
            insert(Provider)
            .values(
                id=provider_1_id,
                business_id=business_id,
                name="Camila Rojas",
                bio="Especialista en cortes estructurados y textura natural con 8 años de experiencia.",
                is_active=True,
                sort_order=1,
            )
            .on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "name": "Camila Rojas",
                    "bio": "Especialista en cortes estructurados y textura natural con 8 años de experiencia.",
                },
            )
        )
        session.execute(stmt)

        provider_2_id = "00000000-0000-0000-0000-000000000202"
        stmt = (
            insert(Provider)
            .values(
                id=provider_2_id,
                business_id=business_id,
                name="Javier Pérez",
                bio="Maestro barbero enfocado en perfilado tradicional y cuidado integral masculino.",
                is_active=True,
                sort_order=2,
            )
            .on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "name": "Javier Pérez",
                    "bio": "Maestro barbero enfocado en perfilado tradicional y cuidado integral masculino.",
                },
            )
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

        # 5. Availability Rules (Monday to Saturday, 0..5)
        rules = []
        rule_idx = 1
        for weekday in range(6):  # Lunes (0) a Sábado (5)
            # Camila: 09:00 - 14:00 & 15:00 - 18:00
            rules.append(
                {
                    "id": f"00000000-0000-0000-0000-{rule_idx:012d}",
                    "business_id": business_id,
                    "provider_id": provider_1_id,
                    "weekday": weekday,
                    "start_time": time(9, 0),
                    "end_time": time(14, 0),
                }
            )
            rule_idx += 1
            rules.append(
                {
                    "id": f"00000000-0000-0000-0000-{rule_idx:012d}",
                    "business_id": business_id,
                    "provider_id": provider_1_id,
                    "weekday": weekday,
                    "start_time": time(15, 0),
                    "end_time": time(18, 0),
                }
            )
            rule_idx += 1

            # Javier: 10:00 - 19:00
            rules.append(
                {
                    "id": f"00000000-0000-0000-0000-{rule_idx:012d}",
                    "business_id": business_id,
                    "provider_id": provider_2_id,
                    "weekday": weekday,
                    "start_time": time(10, 0),
                    "end_time": time(19, 0),
                }
            )
            rule_idx += 1

        for rule in rules:
            stmt = (
                insert(AvailabilityRule)
                .values(rule)
                .on_conflict_do_update(
                    index_elements=["id"],
                    set_={"start_time": rule["start_time"], "end_time": rule["end_time"], "weekday": rule["weekday"]},
                )
            )
            session.execute(stmt)

        session.commit()
        print("Seed data successfully inserted.")


if __name__ == "__main__":
    run_seed()
