import sys
import uuid
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.config import settings
from app.models.admin_user import AdminUser
from app.models.availability import AvailabilityRule, TimeOff
from app.models.booking import Booking, BookingSource, BookingStatus, EmailDeliveryStatus
from app.models.business import Business
from app.models.provider import Provider, ProviderService
from app.models.service import Service


def get_working_day(target_date: date, offset_days: int) -> date:
    """Return a working day (Mon-Sat, 0..5) offset from target_date."""
    candidate = target_date + timedelta(days=offset_days)
    if candidate.weekday() == 6:  # Sunday
        candidate += timedelta(days=1 if offset_days >= 0 else -1)
    return candidate


def run_seed(engine_override=None, *, now: datetime | None = None):
    engine = engine_override or create_engine(settings.DATABASE_URL)

    is_production = settings.APP_ENV.lower() == "production"
    admin_email = (settings.ADMIN_EMAIL or "").strip().lower()
    admin_password = settings.ADMIN_PASSWORD or ""
    admin_display_name = (settings.ADMIN_DISPLAY_NAME or "").strip() or "Administrador"

    # In production, require explicit admin credentials without fallback
    if is_production and (not admin_email or not admin_password):
        raise ValueError("ADMIN_EMAIL y ADMIN_PASSWORD deben estar configurados obligatoriamente en producción.")

    with Session(engine) as session:
        business_id = uuid.UUID(str(settings.BUSINESS_ID))

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
                email="contacto@estudionomada.example.com",
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
                    "email": "contacto@estudionomada.example.com",
                    "phone": "+56912345678",
                    "address": "Calle Valparaíso 123, Viña del Mar",
                    "timezone": "America/Santiago",
                    "locale": "es-CL",
                    "currency": "CLP",
                },
            )
        )
        session.execute(stmt)

        # 2. Admin User (if credentials provided)
        if admin_email and admin_password:
            admin_user_id = uuid.UUID("00000000-0000-0000-0000-000000000099")
            stmt = (
                insert(AdminUser)
                .values(
                    id=admin_user_id,
                    business_id=business_id,
                    email=admin_email,
                    password_hash=hash_password(admin_password),
                    display_name=admin_display_name,
                    is_active=True,
                )
                .on_conflict_do_update(
                    index_elements=["business_id", "email"],
                    set_={
                        "password_hash": hash_password(admin_password),
                        "display_name": admin_display_name,
                        "is_active": True,
                    },
                )
            )
            session.execute(stmt)

        # 3. Services
        service_1_id = uuid.UUID("00000000-0000-0000-0000-000000000101")
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
                    "is_active": True,
                    "sort_order": 1,
                },
            )
        )
        session.execute(stmt)

        service_2_id = uuid.UUID("00000000-0000-0000-0000-000000000102")
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
                    "is_active": True,
                    "sort_order": 2,
                },
            )
        )
        session.execute(stmt)

        # 4. Providers
        provider_1_id = uuid.UUID("00000000-0000-0000-0000-000000000201")
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
                    "is_active": True,
                    "sort_order": 1,
                },
            )
        )
        session.execute(stmt)

        provider_2_id = uuid.UUID("00000000-0000-0000-0000-000000000202")
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
                    "is_active": True,
                    "sort_order": 2,
                },
            )
        )
        session.execute(stmt)

        # 5. Provider Services
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

        # 6. Availability Rules (Monday to Saturday, 0..5)
        rules = []
        rule_idx = 1
        for weekday in range(6):  # Lunes (0) a Sábado (5)
            # Camila: 09:00 - 14:00 & 15:00 - 18:00
            rules.append(
                {
                    "id": uuid.UUID(f"00000000-0000-0000-0000-{rule_idx:012d}"),
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
                    "id": uuid.UUID(f"00000000-0000-0000-0000-{rule_idx:012d}"),
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
                    "id": uuid.UUID(f"00000000-0000-0000-0000-{rule_idx:012d}"),
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

        # 7. TimeOff Block (Camila Rojas, Future technical training block)
        tz_santiago = ZoneInfo("America/Santiago")
        ref_dt = (now or datetime.now(timezone.utc)).astimezone(tz_santiago)
        today_santiago = ref_dt.date()
        future_off_day = get_working_day(today_santiago, offset_days=3)
        time_off_start = datetime(
            future_off_day.year, future_off_day.month, future_off_day.day, 16, 0, tzinfo=tz_santiago
        ).astimezone(timezone.utc)
        time_off_end = time_off_start + timedelta(hours=2)

        time_off_id = uuid.UUID("00000000-0000-0000-0000-000000000301")
        stmt = (
            insert(TimeOff)
            .values(
                id=time_off_id,
                business_id=business_id,
                provider_id=provider_1_id,
                starts_at=time_off_start,
                ends_at=time_off_end,
                reason="Taller de capacitación y perfeccionamiento",
            )
            .on_conflict_do_nothing(index_elements=["id"])
        )
        session.execute(stmt)

        # 8. Demo Bookings (Past & Future non-overlapping)
        past_day = get_working_day(today_santiago, offset_days=-1)
        future_day_1 = get_working_day(today_santiago, offset_days=1)
        future_day_2 = get_working_day(today_santiago, offset_days=2)

        def make_utc_dt(d: date, hour: int, minute: int) -> datetime:
            return datetime(d.year, d.month, d.day, hour, minute, tzinfo=tz_santiago).astimezone(timezone.utc)

        demo_bookings = [
            # Camila - Past completed
            {
                "id": uuid.UUID("00000000-0000-0000-0000-000000000401"),
                "business_id": business_id,
                "service_id": service_1_id,
                "provider_id": provider_1_id,
                "public_reference": "DEMO-2026-001",
                "customer_name": "Matías Silva",
                "customer_email": "matias.silva@example.com",
                "customer_phone": "+56991112233",
                "customer_notes": "Degradado medio con tijera arriba.",
                "starts_at": make_utc_dt(past_day, 10, 0),
                "ends_at": make_utc_dt(past_day, 10, 45),
                "status": BookingStatus.completed,
                "source": BookingSource.public,
                "service_name_snapshot": "Corte de Cabello",
                "duration_minutes_snapshot": 45,
                "price_amount_snapshot": 15000,
                "provider_name_snapshot": "Camila Rojas",
                "email_delivery_status": EmailDeliveryStatus.not_requested,
                "completed_at": make_utc_dt(past_day, 10, 45),
            },
            # Camila - Future confirmed
            {
                "id": uuid.UUID("00000000-0000-0000-0000-000000000402"),
                "business_id": business_id,
                "service_id": service_1_id,
                "provider_id": provider_1_id,
                "public_reference": "DEMO-2026-002",
                "customer_name": "Valentina Morales",
                "customer_email": "valentina.morales@example.com",
                "customer_phone": "+56992223344",
                "customer_notes": "Corte de puntas y texturizado.",
                "starts_at": make_utc_dt(future_day_1, 11, 0),
                "ends_at": make_utc_dt(future_day_1, 11, 45),
                "status": BookingStatus.confirmed,
                "source": BookingSource.public,
                "service_name_snapshot": "Corte de Cabello",
                "duration_minutes_snapshot": 45,
                "price_amount_snapshot": 15000,
                "provider_name_snapshot": "Camila Rojas",
                "email_delivery_status": EmailDeliveryStatus.not_requested,
                "completed_at": None,
            },
            # Camila - Future confirmed (different slot, no overlap)
            {
                "id": uuid.UUID("00000000-0000-0000-0000-000000000403"),
                "business_id": business_id,
                "service_id": service_1_id,
                "provider_id": provider_1_id,
                "public_reference": "DEMO-2026-003",
                "customer_name": "Andrés Castro",
                "customer_email": "andres.castro@example.com",
                "customer_phone": "+56993334455",
                "customer_notes": "",
                "starts_at": make_utc_dt(future_day_1, 12, 0),
                "ends_at": make_utc_dt(future_day_1, 12, 45),
                "status": BookingStatus.confirmed,
                "source": BookingSource.admin,
                "service_name_snapshot": "Corte de Cabello",
                "duration_minutes_snapshot": 45,
                "price_amount_snapshot": 15000,
                "provider_name_snapshot": "Camila Rojas",
                "email_delivery_status": EmailDeliveryStatus.not_requested,
                "completed_at": None,
            },
            # Javier - Past completed (Barba Spa)
            {
                "id": uuid.UUID("00000000-0000-0000-0000-000000000404"),
                "business_id": business_id,
                "service_id": service_2_id,
                "provider_id": provider_2_id,
                "public_reference": "DEMO-2026-004",
                "customer_name": "Diego Soto",
                "customer_email": "diego.soto@example.com",
                "customer_phone": "+56994445566",
                "customer_notes": "Perfilado con navaja tradicional.",
                "starts_at": make_utc_dt(past_day, 11, 30),
                "ends_at": make_utc_dt(past_day, 12, 0),
                "status": BookingStatus.completed,
                "source": BookingSource.public,
                "service_name_snapshot": "Barba Spa",
                "duration_minutes_snapshot": 30,
                "price_amount_snapshot": 10000,
                "provider_name_snapshot": "Javier Pérez",
                "email_delivery_status": EmailDeliveryStatus.not_requested,
                "completed_at": make_utc_dt(past_day, 12, 0),
            },
            # Javier - Future confirmed (Corte)
            {
                "id": uuid.UUID("00000000-0000-0000-0000-000000000405"),
                "business_id": business_id,
                "service_id": service_1_id,
                "provider_id": provider_2_id,
                "public_reference": "DEMO-2026-005",
                "customer_name": "Francisca Navarro",
                "customer_email": "francisca.navarro@example.com",
                "customer_phone": "+56995556677",
                "customer_notes": "",
                "starts_at": make_utc_dt(future_day_2, 14, 0),
                "ends_at": make_utc_dt(future_day_2, 14, 45),
                "status": BookingStatus.confirmed,
                "source": BookingSource.public,
                "service_name_snapshot": "Corte de Cabello",
                "duration_minutes_snapshot": 45,
                "price_amount_snapshot": 15000,
                "provider_name_snapshot": "Javier Pérez",
                "email_delivery_status": EmailDeliveryStatus.not_requested,
                "completed_at": None,
            },
            # Javier - Future confirmed (Barba)
            {
                "id": uuid.UUID("00000000-0000-0000-0000-000000000406"),
                "business_id": business_id,
                "service_id": service_2_id,
                "provider_id": provider_2_id,
                "public_reference": "DEMO-2026-006",
                "customer_name": "Rodrigo Tapia",
                "customer_email": "rodrigo.tapia@example.com",
                "customer_phone": "+56996667788",
                "customer_notes": "Mantenimiento general.",
                "starts_at": make_utc_dt(future_day_2, 15, 30),
                "ends_at": make_utc_dt(future_day_2, 16, 0),
                "status": BookingStatus.confirmed,
                "source": BookingSource.admin,
                "service_name_snapshot": "Barba Spa",
                "duration_minutes_snapshot": 30,
                "price_amount_snapshot": 10000,
                "provider_name_snapshot": "Javier Pérez",
                "email_delivery_status": EmailDeliveryStatus.not_requested,
                "completed_at": None,
            },
        ]

        for b_data in demo_bookings:
            stmt = insert(Booking).values(b_data).on_conflict_do_nothing(index_elements=["id"])
            session.execute(stmt)

        session.commit()
        print("Seed data successfully inserted/updated.")


if __name__ == "__main__":
    run_seed()
