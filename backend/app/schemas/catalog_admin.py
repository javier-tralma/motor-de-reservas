import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

PHONE_REGEX = re.compile(r"^[0-9+() -]{7,32}$")


class AdminServiceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field("", max_length=1000)
    duration_minutes: int = Field(..., ge=5, le=720)
    price_amount: int = Field(..., ge=0)
    is_active: bool = True
    sort_order: int = Field(0, ge=0)

    @field_validator("name", "description", mode="before")
    @classmethod
    def strip_text(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            return v.strip()
        return v


class AdminServiceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=1, max_length=120)
    description: str | None = Field(None, max_length=1000)
    duration_minutes: int | None = Field(None, ge=5, le=720)
    price_amount: int | None = Field(None, ge=0)
    is_active: bool | None = None
    sort_order: int | None = Field(None, ge=0)

    @field_validator("name", "description", mode="before")
    @classmethod
    def strip_text(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            return v.strip()
        return v

    @model_validator(mode="after")
    def validate_non_empty_body(self) -> "AdminServiceUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided for update")

        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")

        return self


class AdminServiceDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    name: str
    description: str
    duration_minutes: int
    price_amount: int
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class AdminProviderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=120)
    email: EmailStr | None = None
    phone: str | None = None
    bio: str = Field("", max_length=1000)
    is_active: bool = True
    sort_order: int = Field(0, ge=0)

    @field_validator("name", "bio", mode="before")
    @classmethod
    def strip_text(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if isinstance(v, str):
            v_stripped = v.strip()
            if not v_stripped:
                return None
            if not PHONE_REGEX.match(v_stripped):
                raise ValueError("Invalid phone format")
            return v_stripped
        return v


class AdminProviderUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=1, max_length=120)
    email: EmailStr | None = None
    phone: str | None = None
    bio: str | None = Field(None, max_length=1000)
    is_active: bool | None = None
    sort_order: int | None = Field(None, ge=0)

    @field_validator("name", "bio", mode="before")
    @classmethod
    def strip_text(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if isinstance(v, str):
            v_stripped = v.strip()
            if not v_stripped:
                return None
            if not PHONE_REGEX.match(v_stripped):
                raise ValueError("Invalid phone format")
            return v_stripped
        return v

    @model_validator(mode="after")
    def validate_non_empty_body(self) -> "AdminProviderUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided for update")

        non_nullable_fields = {"name", "bio", "is_active", "sort_order"}
        for field in self.model_fields_set:
            if field in non_nullable_fields and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")

        return self


class AdminProviderDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    name: str
    email: str | None = None
    phone: str | None = None
    bio: str
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class AdminProviderServicesReplace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_ids: list[uuid.UUID]

    @field_validator("service_ids")
    @classmethod
    def validate_unique_service_ids(cls, v: list[uuid.UUID]) -> list[uuid.UUID]:
        if len(v) != len(set(v)):
            raise ValueError("service_ids contains duplicates")
        return v


class AdminProviderServicesDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: uuid.UUID
    service_ids: list[uuid.UUID]
