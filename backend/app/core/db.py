from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def resolve_migration_database_url(configured_url: str | None, default_url: str) -> str:
    placeholder_url = "driver://user:pass@localhost/dbname"
    if not configured_url or configured_url == placeholder_url:
        return default_url
    return configured_url
