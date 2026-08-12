import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.csrf import verify_origin
from app.core.db import get_db
from app.core.dependencies import get_current_admin
from app.models.admin_user import AdminUser
from app.schemas.admin import ResponseEnvelope
from app.schemas.catalog_admin import (
    AdminServiceCreate,
    AdminServiceDetail,
    AdminServiceUpdate,
)
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/services", tags=["Admin Services"])


def get_catalog_service(db: Annotated[Session, Depends(get_db)]) -> CatalogService:
    return CatalogService(db)


@router.get("", response_model=ResponseEnvelope[list[AdminServiceDetail]])
def list_admin_services(
    current_admin: Annotated[AdminUser, Depends(get_current_admin)],
    service: Annotated[CatalogService, Depends(get_catalog_service)],
) -> ResponseEnvelope[list[AdminServiceDetail]]:
    services = service.list_services(business_id=current_admin.business_id)
    return ResponseEnvelope(data=services)


@router.post("", response_model=ResponseEnvelope[AdminServiceDetail], status_code=201)
def create_admin_service(
    data: AdminServiceCreate,
    current_admin: Annotated[AdminUser, Depends(get_current_admin)],
    service: Annotated[CatalogService, Depends(get_catalog_service)],
    _: Annotated[None, Depends(verify_origin)],
) -> ResponseEnvelope[AdminServiceDetail]:
    created = service.create_service(business_id=current_admin.business_id, data=data)
    return ResponseEnvelope(data=created)


@router.patch("/{service_id}", response_model=ResponseEnvelope[AdminServiceDetail])
def update_admin_service(
    service_id: uuid.UUID,
    data: AdminServiceUpdate,
    current_admin: Annotated[AdminUser, Depends(get_current_admin)],
    service: Annotated[CatalogService, Depends(get_catalog_service)],
    _: Annotated[None, Depends(verify_origin)],
) -> ResponseEnvelope[AdminServiceDetail]:
    updated = service.update_service(business_id=current_admin.business_id, service_id=service_id, data=data)
    return ResponseEnvelope(data=updated)
