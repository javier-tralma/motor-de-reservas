import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKeyConstraint, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.core.db import Base


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), nullable=False)
    email = Column(String(254), nullable=False)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(120), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    __table_args__ = (
        ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        UniqueConstraint("business_id", "email", name="uq_admin_users_business_email"),
        UniqueConstraint("business_id", "id", name="uq_admin_users_business_id"),
        Index("ix_admin_users_business_email", "business_id", "email"),
    )
