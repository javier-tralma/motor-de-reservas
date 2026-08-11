from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.dependencies import get_current_admin
from app.integrations.email.service import FakeEmailService
from app.models.admin_user import AdminUser
from app.schemas.admin import ResponseEnvelope
from app.schemas.booking_admin import AdminProviderListItem
from app.services.availability_service import AvailabilityService
from app.services.booking_service import BookingService

router = APIRouter(prefix="/providers", tags=["Admin Providers"])


def get_booking_service(db: Annotated[Session, Depends(get_db)]) -> BookingService:
    availability_service = AvailabilityService(db)
    email_service = FakeEmailService()
    return BookingService(db, availability_service, email_service)


@router.get("", response_model=ResponseEnvelope[list[AdminProviderListItem]])
def list_admin_providers(
    current_admin: Annotated[AdminUser, Depends(get_current_admin)],
    service: Annotated[BookingService, Depends(get_booking_service)],
) -> ResponseEnvelope[list[AdminProviderListItem]]:
    providers = service.get_admin_providers(business_id=current_admin.business_id)
    return ResponseEnvelope(data=providers)
