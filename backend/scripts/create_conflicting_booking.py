import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.integrations.email.service import NoOpEmailService
from app.schemas.booking import BookingCreateRequest
from app.services.availability_service import AvailabilityService
from app.services.booking_service import BookingService


def validate_e2e_target(db_url_str: str) -> None:
    if not db_url_str:
        sys.exit("Error: DATABASE_URL is not set for helper.")

    try:
        url = make_url(db_url_str)
    except Exception as e:
        sys.exit(f"Error: Invalid DATABASE_URL: {e}")

    host = url.host or ""
    port = url.port or 0
    database = url.database or ""

    if host != "127.0.0.1" or port != 5434 or database != "booking_e2e":
        sys.exit(
            f"Error: Aborting helper. Expected host=127.0.0.1, port=5434, database=booking_e2e. "
            f"Got host={host}, port={port}, database={database}"
        )


def main():
    parser = argparse.ArgumentParser(description="Create a conflicting booking on booking_e2e via domain service")
    parser.add_argument("--starts-at", required=True, help="Starts at in ISO format")
    parser.add_argument("--service-id", default="00000000-0000-0000-0000-000000000010")
    parser.add_argument("--provider-id", default="00000000-0000-0000-0000-000000000020")
    parser.add_argument("--business-id", default="00000000-0000-0000-0000-000000000001")
    parser.add_argument("--name", default="Competitor Booker")
    parser.add_argument("--email", default="competitor@estudionomada.cl")

    parser.add_argument("--phone", default="+56999998888")

    args = parser.parse_args()

    db_url_str = os.environ.get("DATABASE_URL", "")
    validate_e2e_target(db_url_str)

    engine = create_engine(db_url_str)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        b_id = uuid.UUID(args.business_id)
        s_id = uuid.UUID(args.service_id)
        p_id = uuid.UUID(args.provider_id)
        starts_at_dt = datetime.fromisoformat(args.starts_at)

        req = BookingCreateRequest(
            service_id=s_id,
            provider_id=p_id,
            starts_at=starts_at_dt,
            client_request_id=uuid.uuid4(),
            customer_name=args.name,
            customer_email=args.email,
            customer_phone=args.phone,
            customer_notes="Competing reservation created by E2E helper",
        )

        avail_service = AvailabilityService(session)
        email_service = NoOpEmailService()
        booking_service = BookingService(session, avail_service, email_service)

        booking, created = booking_service.create_public_booking(b_id, req)
        print(f"Conflicting booking created successfully: reference={booking.public_reference}, created={created}")
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    main()
