import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
from datetime import time

from alembic.config import Config
from pwdlib import PasswordHash
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from alembic import command
from app.models.admin_user import AdminUser
from app.models.availability import AvailabilityRule
from app.models.business import Business
from app.models.provider import Provider, ProviderService
from app.models.service import Service


def validate_e2e_target(db_url_str: str) -> None:
    if not db_url_str:
        sys.exit("Error: DATABASE_URL is not set for E2E setup.")

    try:
        url = make_url(db_url_str)
    except Exception as e:
        sys.exit(f"Error: Invalid DATABASE_URL: {e}")

    host = url.host or ""
    port = url.port or 0
    database = url.database or ""

    if host != "127.0.0.1" or port != 5434 or database != "booking_e2e":
        sys.exit(
            f"Error: Aborting E2E setup. Expected host=127.0.0.1, port=5434, database=booking_e2e. "
            f"Got host={host}, port={port}, database={database}"
        )


def main():
    db_url_str = os.environ.get("DATABASE_URL", "")
    validate_e2e_target(db_url_str)

    print("Target validated: booking_e2e on port 5434. Resetting schema...")
    engine = create_engine(db_url_str)

    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
        conn.commit()

    print("Applying Alembic migrations to booking_e2e...")
    alembic_ini_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic.ini")
    alembic_cfg = Config(alembic_ini_path)
    alembic_cfg.set_main_option("sqlalchemy.url", db_url_str)
    command.upgrade(alembic_cfg, "head")

    print("Seeding E2E deterministic test data...")
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        b_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        s_id = uuid.UUID("00000000-0000-0000-0000-000000000010")
        p_id = uuid.UUID("00000000-0000-0000-0000-000000000020")
        admin_id = uuid.UUID("00000000-0000-0000-0000-000000000030")

        business = Business(
            id=b_id,
            name="Estudio Nómada E2E",
            slug="estudio-nomada",
            email="contacto@estudionomada.cl",
            timezone="America/Santiago",
            locale="es-CL",
            currency="CLP",
            minimum_booking_notice_minutes=0,
            booking_horizon_days=60,
            slot_interval_minutes=30,
        )
        session.add(business)
        session.flush()

        service = Service(
            id=s_id,
            business_id=b_id,
            name="Corte y Barba E2E",
            description="Servicio completo de barbería E2E",
            duration_minutes=30,
            price_amount=18000,
            is_active=True,
            sort_order=0,
        )
        session.add(service)

        provider = Provider(
            id=p_id,
            business_id=b_id,
            name="Barbero Experto E2E",
            email="barbero@estudionomada.cl",
            bio="Especialista en cortes clásicos",
            is_active=True,
            sort_order=0,
        )
        session.add(provider)
        session.flush()

        ps = ProviderService(
            business_id=b_id,
            provider_id=p_id,
            service_id=s_id,
        )
        session.add(ps)

        # Add weekly rules Monday (0) through Sunday (6) from 08:00 to 20:00
        for weekday in range(7):
            rule = AvailabilityRule(
                id=uuid.uuid4(),
                business_id=b_id,
                provider_id=p_id,
                weekday=weekday,
                start_time=time(8, 0),
                end_time=time(20, 0),
            )
            session.add(rule)

        # Seed admin user
        password_hash = PasswordHash.recommended()
        hashed = password_hash.hash("AdminE2E2026!")

        admin = AdminUser(
            id=admin_id,
            business_id=b_id,
            email="admin@estudionomada.cl",
            password_hash=hashed,
            display_name="Admin E2E",
            is_active=True,
        )

        session.add(admin)

        session.commit()
        print("E2E database setup and seeding complete.")
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    main()
