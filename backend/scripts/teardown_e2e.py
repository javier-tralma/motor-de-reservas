import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def validate_e2e_target(db_url_str: str) -> None:
    if not db_url_str:
        sys.exit("Error: DATABASE_URL is not set for E2E teardown.")

    try:
        url = make_url(db_url_str)
    except Exception as e:
        sys.exit(f"Error: Invalid DATABASE_URL: {e}")

    host = url.host or ""
    port = url.port or 0
    database = url.database or ""

    if host != "127.0.0.1" or port != 5434 or database != "booking_e2e":
        sys.exit(
            f"Error: Aborting E2E teardown. Expected host=127.0.0.1, port=5434, database=booking_e2e. "
            f"Got host={host}, port={port}, database={database}"
        )


def main():
    db_url_str = os.environ.get("DATABASE_URL", "")
    validate_e2e_target(db_url_str)

    print("Target validated: booking_e2e on port 5434. Executing teardown...")
    engine = create_engine(db_url_str)

    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
        conn.commit()

    engine.dispose()
    print("E2E database teardown complete.")


if __name__ == "__main__":
    main()
