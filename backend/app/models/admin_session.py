import uuid

from sqlalchemy import Column, DateTime, ForeignKeyConstraint, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.core.db import Base


class AdminSession(Base):
    __tablename__ = "admin_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), nullable=False)
    admin_user_id = Column(UUID(as_uuid=True), nullable=False)
    token_hash = Column(String(128), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())

    __table_args__ = (
        ForeignKeyConstraint(
            ["business_id", "admin_user_id"],
            ["admin_users.business_id", "admin_users.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("token_hash", name="uq_admin_sessions_token_hash"),
        Index("ix_admin_sessions_admin_user_revoked", "admin_user_id", "revoked_at"),
        Index("ix_admin_sessions_expires_at", "expires_at"),
    )
