import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class CalendarEventItem(BaseModel):
    id: uuid.UUID
    kind: Literal["booking", "time_off"]
    starts_at: datetime
    ends_at: datetime
    provider_id: uuid.UUID
    provider_name: str
    booking_status: str | None
    customer_display_name: str | None
    service_name: str | None
    reason: str | None


class CalendarEventsData(BaseModel):
    timezone: str
    events: list[CalendarEventItem]
