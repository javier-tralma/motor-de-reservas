from datetime import datetime, timezone
from typing import Callable, Optional
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.endpoints.availability import DomainError
from app.domain.time_utils import NonExistentTimeError, create_aware_datetime, get_now
from app.models.availability import AvailabilityRule, TimeOff
from app.models.business import Business
from app.models.provider import Provider
from app.schemas.availability_admin import AdminAvailabilityRuleItem, AdminTimeOffCreate


class AvailabilityAdminService:
    def __init__(self, db: Session, get_now_fn: Optional[Callable[[str], datetime]] = None):
        self.db = db
        self.get_now_fn = get_now_fn or get_now

    def get_provider_availability_rules(self, business_id: UUID, provider_id: UUID) -> list[AvailabilityRule]:
        provider = self.db.execute(
            select(Provider).filter_by(id=provider_id, business_id=business_id)
        ).scalar_one_or_none()
        if not provider:
            raise DomainError(code="provider_not_found", message="Provider not found", status_code=404)

        rules = (
            self.db.execute(
                select(AvailabilityRule)
                .filter_by(business_id=business_id, provider_id=provider_id)
                .order_by(AvailabilityRule.weekday.asc(), AvailabilityRule.start_time.asc())
            )
            .scalars()
            .all()
        )
        return list(rules)

    def replace_provider_availability_rules(
        self, business_id: UUID, provider_id: UUID, rules: list[AdminAvailabilityRuleItem]
    ) -> list[AvailabilityRule]:
        # Lock provider row to serialize concurrent replacements
        provider = self.db.execute(
            select(Provider).filter_by(id=provider_id, business_id=business_id).with_for_update()
        ).scalar_one_or_none()
        if not provider:
            raise DomainError(code="provider_not_found", message="Provider not found", status_code=404)

        # Delete existing rules
        self.db.execute(delete(AvailabilityRule).filter_by(business_id=business_id, provider_id=provider_id))

        # Insert new rules
        for r in rules:
            new_rule = AvailabilityRule(
                business_id=business_id,
                provider_id=provider_id,
                weekday=r.weekday,
                start_time=r.start_time,
                end_time=r.end_time,
            )
            self.db.add(new_rule)

        self.db.commit()

        saved_rules = (
            self.db.execute(
                select(AvailabilityRule)
                .filter_by(business_id=business_id, provider_id=provider_id)
                .order_by(AvailabilityRule.weekday.asc(), AvailabilityRule.start_time.asc())
            )
            .scalars()
            .all()
        )
        return list(saved_rules)

    def list_provider_time_offs(
        self, business_id: UUID, provider_id: UUID, now_dt: Optional[datetime] = None
    ) -> list[TimeOff]:
        provider = self.db.execute(
            select(Provider).filter_by(id=provider_id, business_id=business_id)
        ).scalar_one_or_none()
        if not provider:
            raise DomainError(code="provider_not_found", message="Provider not found", status_code=404)

        ref_now = now_dt or self.get_now_fn("UTC")
        if ref_now.tzinfo is None:
            ref_now = ref_now.replace(tzinfo=timezone.utc)
        ref_now_utc = ref_now.astimezone(timezone.utc)

        time_offs = (
            self.db.execute(
                select(TimeOff)
                .filter(
                    TimeOff.business_id == business_id,
                    TimeOff.provider_id == provider_id,
                    TimeOff.ends_at > ref_now_utc,
                )
                .order_by(TimeOff.starts_at.asc(), TimeOff.id.asc())
            )
            .scalars()
            .all()
        )
        return list(time_offs)

    def create_time_off(self, business_id: UUID, data: AdminTimeOffCreate) -> TimeOff:
        # Check provider exists in business (can be active or inactive)
        provider = self.db.execute(
            select(Provider).filter_by(id=data.provider_id, business_id=business_id)
        ).scalar_one_or_none()
        if not provider:
            raise DomainError(code="provider_not_found", message="Provider not found", status_code=404)

        business = self.db.execute(select(Business).filter_by(id=business_id)).scalar_one_or_none()
        if not business:
            raise DomainError(code="business_not_found", message="Business not found", status_code=404)

        # Parse local civil datetimes
        try:
            start_dt_unaware = datetime.fromisoformat(data.starts_at_local)
            end_dt_unaware = datetime.fromisoformat(data.ends_at_local)
        except Exception as e:
            raise DomainError(
                code="invalid_time_format", message=f"Invalid local datetime format: {e}", status_code=422
            ) from e

        # Resolve with business timezone and fold=0
        try:
            start_aware = create_aware_datetime(
                start_dt_unaware.date(), start_dt_unaware.time(), tz_name=business.timezone, fold=0
            )
        except NonExistentTimeError as e:
            raise DomainError(
                code="non_existent_local_time",
                message="La fecha u hora de inicio seleccionada no existe debido al cambio de horario.",
                status_code=422,
            ) from e

        try:
            end_aware = create_aware_datetime(
                end_dt_unaware.date(), end_dt_unaware.time(), tz_name=business.timezone, fold=0
            )
        except NonExistentTimeError as e:
            raise DomainError(
                code="non_existent_local_time",
                message="La fecha u hora de término seleccionada no existe debido al cambio de horario.",
                status_code=422,
            ) from e

        starts_at_utc = start_aware.astimezone(timezone.utc)
        ends_at_utc = end_aware.astimezone(timezone.utc)

        if starts_at_utc >= ends_at_utc:
            raise DomainError(
                code="invalid_time_range",
                message="La fecha y hora de término debe ser posterior al inicio.",
                status_code=422,
            )

        time_off = TimeOff(
            business_id=business_id,
            provider_id=data.provider_id,
            starts_at=starts_at_utc,
            ends_at=ends_at_utc,
            reason=data.reason,
        )
        self.db.add(time_off)
        self.db.commit()
        self.db.refresh(time_off)
        return time_off

    def delete_time_off(self, business_id: UUID, time_off_id: UUID) -> None:
        time_off = self.db.execute(
            select(TimeOff).filter_by(id=time_off_id, business_id=business_id)
        ).scalar_one_or_none()
        if not time_off:
            raise DomainError(code="time_off_not_found", message="Time off not found", status_code=404)

        self.db.delete(time_off)
        self.db.commit()
