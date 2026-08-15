import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.csrf import verify_origin
from app.core.db import get_db
from app.core.dependencies import get_current_admin
from app.models.admin_user import AdminUser
from app.schemas.admin import ResponseEnvelope
from app.schemas.availability_admin import (
    AdminAvailabilityRuleItem,
    AdminAvailabilityRulesReplace,
)
from app.schemas.booking_admin import AdminProviderListItem
from app.schemas.catalog_admin import (
    AdminProviderCreate,
    AdminProviderDetail,
    AdminProviderServicesDetail,
    AdminProviderServicesReplace,
    AdminProviderUpdate,
)
from app.services.availability_admin_service import AvailabilityAdminService
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/providers", tags=["Admin Providers"])


def get_catalog_service(db: Annotated[Session, Depends(get_db)]) -> CatalogService:
    return CatalogService(db)


def get_availability_admin_service(db: Annotated[Session, Depends(get_db)]) -> AvailabilityAdminService:
    return AvailabilityAdminService(db)


@router.get("", response_model=ResponseEnvelope[list[AdminProviderListItem]])
def list_admin_providers(
    current_admin: Annotated[AdminUser, Depends(get_current_admin)],
    service: Annotated[CatalogService, Depends(get_catalog_service)],
    service_id: Annotated[uuid.UUID | None, Query()] = None,
) -> ResponseEnvelope[list[AdminProviderListItem]]:
    providers = service.list_providers(business_id=current_admin.business_id, service_id=service_id)
    return ResponseEnvelope(data=providers)


@router.get("/{provider_id}", response_model=ResponseEnvelope[AdminProviderDetail])
def get_admin_provider_detail(
    provider_id: uuid.UUID,
    current_admin: Annotated[AdminUser, Depends(get_current_admin)],
    service: Annotated[CatalogService, Depends(get_catalog_service)],
) -> ResponseEnvelope[AdminProviderDetail]:
    detail = service.get_provider_detail(business_id=current_admin.business_id, provider_id=provider_id)
    return ResponseEnvelope(data=detail)


@router.post("", response_model=ResponseEnvelope[AdminProviderDetail], status_code=201)
def create_admin_provider(
    data: AdminProviderCreate,
    current_admin: Annotated[AdminUser, Depends(get_current_admin)],
    service: Annotated[CatalogService, Depends(get_catalog_service)],
    _: Annotated[None, Depends(verify_origin)],
) -> ResponseEnvelope[AdminProviderDetail]:
    created = service.create_provider(business_id=current_admin.business_id, data=data)
    return ResponseEnvelope(data=created)


@router.patch("/{provider_id}", response_model=ResponseEnvelope[AdminProviderDetail])
def update_admin_provider(
    provider_id: uuid.UUID,
    data: AdminProviderUpdate,
    current_admin: Annotated[AdminUser, Depends(get_current_admin)],
    service: Annotated[CatalogService, Depends(get_catalog_service)],
    _: Annotated[None, Depends(verify_origin)],
) -> ResponseEnvelope[AdminProviderDetail]:
    updated = service.update_provider(business_id=current_admin.business_id, provider_id=provider_id, data=data)
    return ResponseEnvelope(data=updated)


@router.get("/{provider_id}/services", response_model=ResponseEnvelope[AdminProviderServicesDetail])
def get_admin_provider_services(
    provider_id: uuid.UUID,
    current_admin: Annotated[AdminUser, Depends(get_current_admin)],
    service: Annotated[CatalogService, Depends(get_catalog_service)],
) -> ResponseEnvelope[AdminProviderServicesDetail]:
    detail = service.get_provider_services(business_id=current_admin.business_id, provider_id=provider_id)
    return ResponseEnvelope(data=detail)


@router.put("/{provider_id}/services", response_model=ResponseEnvelope[AdminProviderServicesDetail])
def replace_admin_provider_services(
    provider_id: uuid.UUID,
    data: AdminProviderServicesReplace,
    current_admin: Annotated[AdminUser, Depends(get_current_admin)],
    service: Annotated[CatalogService, Depends(get_catalog_service)],
    _: Annotated[None, Depends(verify_origin)],
) -> ResponseEnvelope[AdminProviderServicesDetail]:
    replaced = service.replace_provider_services(
        business_id=current_admin.business_id, provider_id=provider_id, service_ids=data.service_ids
    )
    return ResponseEnvelope(data=replaced)


@router.get("/{provider_id}/availability-rules", response_model=ResponseEnvelope[list[AdminAvailabilityRuleItem]])
def get_admin_provider_availability_rules(
    provider_id: uuid.UUID,
    current_admin: Annotated[AdminUser, Depends(get_current_admin)],
    avail_service: Annotated[AvailabilityAdminService, Depends(get_availability_admin_service)],
) -> ResponseEnvelope[list[AdminAvailabilityRuleItem]]:
    rules = avail_service.get_provider_availability_rules(
        business_id=current_admin.business_id, provider_id=provider_id
    )
    items = [AdminAvailabilityRuleItem(weekday=r.weekday, start_time=r.start_time, end_time=r.end_time) for r in rules]
    return ResponseEnvelope(data=items)


@router.put("/{provider_id}/availability-rules", response_model=ResponseEnvelope[list[AdminAvailabilityRuleItem]])
def replace_admin_provider_availability_rules(
    provider_id: uuid.UUID,
    data: AdminAvailabilityRulesReplace,
    current_admin: Annotated[AdminUser, Depends(get_current_admin)],
    avail_service: Annotated[AvailabilityAdminService, Depends(get_availability_admin_service)],
    _: Annotated[None, Depends(verify_origin)],
) -> ResponseEnvelope[list[AdminAvailabilityRuleItem]]:
    rules = avail_service.replace_provider_availability_rules(
        business_id=current_admin.business_id, provider_id=provider_id, rules=data.rules
    )
    items = [AdminAvailabilityRuleItem(weekday=r.weekday, start_time=r.start_time, end_time=r.end_time) for r in rules]
    return ResponseEnvelope(data=items)
