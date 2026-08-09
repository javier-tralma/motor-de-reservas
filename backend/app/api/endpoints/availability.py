import uuid
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.services.availability_service import AvailabilityService


def get_availability_service(db: Session = Depends(get_db)) -> AvailabilityService:
    return AvailabilityService(db)


router = APIRouter()


class SlotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    starts_at: datetime
    ends_at: datetime


class AvailabilityData(BaseModel):
    date: date
    service_id: uuid.UUID
    provider_id: Optional[uuid.UUID]
    timezone: str
    slots: List[SlotResponse]


class AvailabilityResponse(BaseModel):
    data: AvailabilityData


class DomainError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code


@router.get("/public/availability", response_model=AvailabilityResponse)
def get_availability(
    service_id: uuid.UUID = Query(...),
    date: date = Query(...),
    provider_id: Optional[uuid.UUID] = Query(None),
    service: AvailabilityService = Depends(get_availability_service),
):
    try:
        result = service.get_availability(
            business_id=settings.BUSINESS_ID, service_id=service_id, target_date=date, provider_id=provider_id
        )  # noqa: E501

        slots = result["slots"]

        # Filtrar o agrupar si provider_id es nulo (Cualquier profesional)
        # La agrupación por starts_at, ends_at significa desduplicar y omitir provider_id
        seen = set()
        response_slots = []
        for s in slots:
            key = (s.starts_at, s.ends_at)
            if key not in seen:
                seen.add(key)
                response_slots.append(SlotResponse(starts_at=s.starts_at, ends_at=s.ends_at))

        # Always order deterministically by starts_at
        response_slots.sort(key=lambda x: x.starts_at)

        return AvailabilityResponse(
            data=AvailabilityData(
                date=date,
                service_id=service_id,
                provider_id=provider_id,
                timezone=result["timezone"],
                slots=response_slots,
            )
        )  # noqa: E501
    except ValueError as e:
        if str(e) == "Service not found or inactive":
            raise DomainError(code="service_unavailable", message=str(e), status_code=404)
        raise DomainError(code="bad_request", message=str(e), status_code=400)
