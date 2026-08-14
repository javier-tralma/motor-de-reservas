import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.dependencies import get_current_admin
from app.models.admin_user import AdminUser
from app.schemas.admin import ResponseEnvelope
from app.schemas.calendar import CalendarEventsData
from app.services.calendar_events_service import CalendarEventsService

router = APIRouter(prefix="/calendar-events", tags=["Admin Calendar"])


def get_calendar_events_service(db: Annotated[Session, Depends(get_db)]) -> CalendarEventsService:
    return CalendarEventsService(db)


@router.get("", response_model=ResponseEnvelope[CalendarEventsData])
def list_admin_calendar_events(
    start: Annotated[date, Query(..., description="Start date (inclusive, YYYY-MM-DD)")],
    end: Annotated[date, Query(..., description="End date (exclusive, YYYY-MM-DD)")],
    current_admin: Annotated[AdminUser, Depends(get_current_admin)],
    service: Annotated[CalendarEventsService, Depends(get_calendar_events_service)],
    provider_id: Annotated[uuid.UUID | None, Query(description="Provider ID")] = None,
) -> ResponseEnvelope[CalendarEventsData]:
    data = service.get_calendar_events(
        business_id=current_admin.business_id,
        start_date=start,
        end_date=end,
        provider_id=provider_id,
    )
    return ResponseEnvelope(data=data)
