import re
from datetime import time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CIVIL_DATETIME_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?$")


class AdminAvailabilityRuleItem(BaseModel):
    weekday: int = Field(..., ge=0, le=6, description="0=Lunes, 6=Domingo")
    start_time: time
    end_time: time

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_time_order(self) -> "AdminAvailabilityRuleItem":
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be earlier than end_time")
        return self


class AdminAvailabilityRulesReplace(BaseModel):
    rules: list[AdminAvailabilityRuleItem]

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_no_overlapping_rules(self) -> "AdminAvailabilityRulesReplace":
        # Group by weekday
        by_weekday: dict[int, list[AdminAvailabilityRuleItem]] = {}
        for r in self.rules:
            by_weekday.setdefault(r.weekday, []).append(r)

        for weekday, day_rules in by_weekday.items():
            # Sort by start_time
            sorted_rules = sorted(day_rules, key=lambda x: x.start_time)
            for i in range(len(sorted_rules)):
                for j in range(i + 1, len(sorted_rules)):
                    r1 = sorted_rules[i]
                    r2 = sorted_rules[j]
                    # Semi-open interval overlap: a_start < b_end and b_start < a_end
                    if r1.start_time < r2.end_time and r2.start_time < r1.end_time:
                        raise ValueError(
                            f"Overlapping intervals on weekday {weekday}: "
                            f"{r1.start_time}-{r1.end_time} and {r2.start_time}-{r2.end_time}"
                        )
        return self


class AdminTimeOffCreate(BaseModel):
    provider_id: UUID
    starts_at_local: str
    ends_at_local: str
    reason: str | None = Field(default=None, max_length=240)

    model_config = ConfigDict(extra="forbid")

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if isinstance(v, str):
            stripped = v.strip()
            return stripped if stripped else None
        return v

    @field_validator("starts_at_local", "ends_at_local")
    @classmethod
    def validate_civil_datetime_format(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Local datetime must be a string in format YYYY-MM-DDTHH:MM[:SS]")
        # Explicitly reject offsets, Z, or timezone identifiers
        if "Z" in v or "z" in v or "+" in v:
            raise ValueError("Local datetime string must not contain timezone offset or Z")
        # Check if contains negative sign in time portion (e.g. 2026-08-15T09:00:00-04:00)
        time_part = v.split("T")[-1] if "T" in v else ""
        if "-" in time_part:
            raise ValueError("Local datetime string must not contain timezone offset")
        if not CIVIL_DATETIME_REGEX.match(v):
            raise ValueError("Local datetime must be in format YYYY-MM-DDTHH:MM or YYYY-MM-DDTHH:MM:SS")
        return v


class AdminTimeOffDetail(BaseModel):
    id: UUID
    provider_id: UUID
    starts_at: str
    ends_at: str
    reason: str | None
    created_at: str
    updated_at: str

    model_config = ConfigDict(extra="forbid")
