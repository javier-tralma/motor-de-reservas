import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.csrf import verify_origin
from app.core.db import get_db
from app.core.dependencies import get_current_admin
from app.domain.time_utils import format_local_iso
from app.models.admin_user import AdminUser
from app.models.availability import TimeOff
from app.models.business import Business
from app.schemas.admin import ResponseEnvelope
from app.schemas.availability_admin import AdminTimeOffCreate, AdminTimeOffDetail
from app.services.availability_admin_service import AvailabilityAdminService

router = APIRouter(prefix="/time-off", tags=["Admin Time Off"])


def get_availability_admin_service(db: Annotated[Session, Depends(get_db)]) -> AvailabilityAdminService:
    return AvailabilityAdminService(db)


def _serialize_time_off(to: TimeOff, timezone_name: str) -> AdminTimeOffDetail:
    return AdminTimeOffDetail(
        id=to.id,
        provider_id=to.provider_id,
        starts_at=format_local_iso(to.starts_at, timezone_name),
        ends_at=format_local_iso(to.ends_at, timezone_name),
        reason=to.reason,
        created_at=format_local_iso(to.created_at, timezone_name),
        updated_at=format_local_iso(to.updated_at, timezone_name),
    )


@router.get("", response_model=ResponseEnvelope[list[AdminTimeOffDetail]])
def list_admin_time_offs(
    provider_id: Annotated[uuid.UUID, Query(..., description="UUID del profesional (obligatorio)")],
    current_admin: Annotated[AdminUser, Depends(get_current_admin)],
    service: Annotated[AvailabilityAdminService, Depends(get_availability_admin_service)],
    db: Annotated[Session, Depends(get_db)],
) -> ResponseEnvelope[list[AdminTimeOffDetail]]:
    business = db.execute(select(Business).filter_by(id=current_admin.business_id)).scalar_one()
    time_offs = service.list_provider_time_offs(business_id=current_admin.business_id, provider_id=provider_id)
    items = [_serialize_time_off(to, business.timezone) for to in time_offs]
    return ResponseEnvelope(data=items)


@router.post("", response_model=ResponseEnvelope[AdminTimeOffDetail], status_code=status.HTTP_201_CREATED)
def create_admin_time_off(
    data: AdminTimeOffCreate,
    current_admin: Annotated[AdminUser, Depends(get_current_admin)],
    service: Annotated[AvailabilityAdminService, Depends(get_availability_admin_service)],
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[None, Depends(verify_origin)],
) -> ResponseEnvelope[AdminTimeOffDetail]:
    business = db.execute(select(Business).filter_by(id=current_admin.business_id)).scalar_one()
    created = service.create_time_off(business_id=current_admin.business_id, data=data)
    detail = _serialize_time_off(created, business.timezone)
    return ResponseEnvelope(data=detail)


@router.delete("/{time_off_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_time_off(
    time_off_id: uuid.UUID,
    current_admin: Annotated[AdminUser, Depends(get_current_admin)],
    service: Annotated[AvailabilityAdminService, Depends(get_availability_admin_service)],
    _: Annotated[None, Depends(verify_origin)],
) -> Response:
    service.delete_time_off(business_id=current_admin.business_id, time_off_id=time_off_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
