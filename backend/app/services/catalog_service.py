import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.endpoints.availability import DomainError
from app.models.business import Business
from app.models.provider import Provider, ProviderService
from app.models.service import Service
from app.schemas.booking_admin import AdminProviderListItem
from app.schemas.catalog_admin import (
    AdminProviderCreate,
    AdminProviderDetail,
    AdminProviderServicesDetail,
    AdminProviderUpdate,
    AdminServiceCreate,
    AdminServiceDetail,
    AdminServiceUpdate,
)


class CatalogService:
    def __init__(self, db: Session):
        self.db = db

    def list_services(self, business_id: uuid.UUID) -> list[AdminServiceDetail]:
        business = self.db.execute(select(Business).filter_by(id=business_id)).scalar_one_or_none()
        if not business:
            raise DomainError(code="business_not_found", message="Business not found", status_code=404)
        local_tz = ZoneInfo(business.timezone)

        def to_local(dt: datetime) -> datetime:
            dt_utc = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            return dt_utc.astimezone(local_tz)

        stmt = select(Service).filter_by(business_id=business_id).order_by(Service.sort_order.asc(), Service.name.asc())
        services = self.db.execute(stmt).scalars().all()
        return [
            AdminServiceDetail(
                id=s.id,
                name=s.name,
                description=s.description,
                duration_minutes=s.duration_minutes,
                price_amount=s.price_amount,
                is_active=s.is_active,
                sort_order=s.sort_order,
                created_at=to_local(s.created_at),
                updated_at=to_local(s.updated_at),
            )
            for s in services
        ]

    def create_service(self, business_id: uuid.UUID, data: AdminServiceCreate) -> AdminServiceDetail:
        business = self.db.execute(select(Business).filter_by(id=business_id)).scalar_one_or_none()
        if not business:
            raise DomainError(code="business_not_found", message="Business not found", status_code=404)
        local_tz = ZoneInfo(business.timezone)

        def to_local(dt: datetime) -> datetime:
            dt_utc = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            return dt_utc.astimezone(local_tz)

        service = Service(
            id=uuid.uuid4(),
            business_id=business_id,
            name=data.name,
            description=data.description,
            duration_minutes=data.duration_minutes,
            price_amount=data.price_amount,
            is_active=data.is_active,
            sort_order=data.sort_order,
        )
        self.db.add(service)
        self.db.commit()
        self.db.refresh(service)

        return AdminServiceDetail(
            id=service.id,
            name=service.name,
            description=service.description,
            duration_minutes=service.duration_minutes,
            price_amount=service.price_amount,
            is_active=service.is_active,
            sort_order=service.sort_order,
            created_at=to_local(service.created_at),
            updated_at=to_local(service.updated_at),
        )

    def update_service(
        self, business_id: uuid.UUID, service_id: uuid.UUID, data: AdminServiceUpdate
    ) -> AdminServiceDetail:
        business = self.db.execute(select(Business).filter_by(id=business_id)).scalar_one_or_none()
        if not business:
            raise DomainError(code="business_not_found", message="Business not found", status_code=404)
        local_tz = ZoneInfo(business.timezone)

        def to_local(dt: datetime) -> datetime:
            dt_utc = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            return dt_utc.astimezone(local_tz)

        service = self.db.execute(
            select(Service).filter_by(id=service_id, business_id=business_id)
        ).scalar_one_or_none()
        if not service:
            raise DomainError(code="service_not_found", message="Service not found", status_code=404)

        fields_to_update = data.model_fields_set
        if "name" in fields_to_update:
            service.name = data.name
        if "description" in fields_to_update:
            service.description = data.description
        if "duration_minutes" in fields_to_update:
            service.duration_minutes = data.duration_minutes
        if "price_amount" in fields_to_update:
            service.price_amount = data.price_amount
        if "is_active" in fields_to_update:
            service.is_active = data.is_active
        if "sort_order" in fields_to_update:
            service.sort_order = data.sort_order

        self.db.commit()
        self.db.refresh(service)

        return AdminServiceDetail(
            id=service.id,
            name=service.name,
            description=service.description,
            duration_minutes=service.duration_minutes,
            price_amount=service.price_amount,
            is_active=service.is_active,
            sort_order=service.sort_order,
            created_at=to_local(service.created_at),
            updated_at=to_local(service.updated_at),
        )

    def list_providers(self, business_id: uuid.UUID) -> list[AdminProviderListItem]:
        stmt = (
            select(Provider).filter_by(business_id=business_id).order_by(Provider.sort_order.asc(), Provider.name.asc())
        )
        providers = self.db.execute(stmt).scalars().all()
        return [
            AdminProviderListItem(
                id=p.id,
                name=p.name,
                is_active=p.is_active,
            )
            for p in providers
        ]

    def get_provider_detail(self, business_id: uuid.UUID, provider_id: uuid.UUID) -> AdminProviderDetail:
        business = self.db.execute(select(Business).filter_by(id=business_id)).scalar_one_or_none()
        if not business:
            raise DomainError(code="business_not_found", message="Business not found", status_code=404)
        local_tz = ZoneInfo(business.timezone)

        def to_local(dt: datetime) -> datetime:
            dt_utc = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            return dt_utc.astimezone(local_tz)

        provider = self.db.execute(
            select(Provider).filter_by(id=provider_id, business_id=business_id)
        ).scalar_one_or_none()
        if not provider:
            raise DomainError(code="provider_not_found", message="Provider not found", status_code=404)

        return AdminProviderDetail(
            id=provider.id,
            name=provider.name,
            email=provider.email,
            phone=provider.phone,
            bio=provider.bio,
            is_active=provider.is_active,
            sort_order=provider.sort_order,
            created_at=to_local(provider.created_at),
            updated_at=to_local(provider.updated_at),
        )

    def create_provider(self, business_id: uuid.UUID, data: AdminProviderCreate) -> AdminProviderDetail:
        business = self.db.execute(select(Business).filter_by(id=business_id)).scalar_one_or_none()
        if not business:
            raise DomainError(code="business_not_found", message="Business not found", status_code=404)
        local_tz = ZoneInfo(business.timezone)

        def to_local(dt: datetime) -> datetime:
            dt_utc = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            return dt_utc.astimezone(local_tz)

        provider = Provider(
            id=uuid.uuid4(),
            business_id=business_id,
            name=data.name,
            email=data.email,
            phone=data.phone,
            bio=data.bio,
            is_active=data.is_active,
            sort_order=data.sort_order,
        )
        self.db.add(provider)
        self.db.commit()
        self.db.refresh(provider)

        return AdminProviderDetail(
            id=provider.id,
            name=provider.name,
            email=provider.email,
            phone=provider.phone,
            bio=provider.bio,
            is_active=provider.is_active,
            sort_order=provider.sort_order,
            created_at=to_local(provider.created_at),
            updated_at=to_local(provider.updated_at),
        )

    def update_provider(
        self, business_id: uuid.UUID, provider_id: uuid.UUID, data: AdminProviderUpdate
    ) -> AdminProviderDetail:
        business = self.db.execute(select(Business).filter_by(id=business_id)).scalar_one_or_none()
        if not business:
            raise DomainError(code="business_not_found", message="Business not found", status_code=404)
        local_tz = ZoneInfo(business.timezone)

        def to_local(dt: datetime) -> datetime:
            dt_utc = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            return dt_utc.astimezone(local_tz)

        provider = self.db.execute(
            select(Provider).filter_by(id=provider_id, business_id=business_id)
        ).scalar_one_or_none()
        if not provider:
            raise DomainError(code="provider_not_found", message="Provider not found", status_code=404)

        fields_to_update = data.model_fields_set
        if "name" in fields_to_update:
            provider.name = data.name
        if "email" in fields_to_update:
            provider.email = data.email
        if "phone" in fields_to_update:
            provider.phone = data.phone
        if "bio" in fields_to_update:
            provider.bio = data.bio
        if "is_active" in fields_to_update:
            provider.is_active = data.is_active
        if "sort_order" in fields_to_update:
            provider.sort_order = data.sort_order

        self.db.commit()
        self.db.refresh(provider)

        return AdminProviderDetail(
            id=provider.id,
            name=provider.name,
            email=provider.email,
            phone=provider.phone,
            bio=provider.bio,
            is_active=provider.is_active,
            sort_order=provider.sort_order,
            created_at=to_local(provider.created_at),
            updated_at=to_local(provider.updated_at),
        )

    def get_provider_services(self, business_id: uuid.UUID, provider_id: uuid.UUID) -> AdminProviderServicesDetail:
        provider = self.db.execute(
            select(Provider).filter_by(id=provider_id, business_id=business_id)
        ).scalar_one_or_none()
        if not provider:
            raise DomainError(code="provider_not_found", message="Provider not found", status_code=404)

        stmt = select(ProviderService.service_id).filter_by(business_id=business_id, provider_id=provider_id)
        service_ids = self.db.execute(stmt).scalars().all()

        return AdminProviderServicesDetail(provider_id=provider_id, service_ids=list(service_ids))

    def replace_provider_services(
        self, business_id: uuid.UUID, provider_id: uuid.UUID, service_ids: list[uuid.UUID]
    ) -> AdminProviderServicesDetail:
        # Lock provider with SELECT ... FOR UPDATE to serialize concurrent replacements
        provider = self.db.execute(
            select(Provider).filter_by(id=provider_id, business_id=business_id).with_for_update()
        ).scalar_one_or_none()

        if not provider:
            raise DomainError(code="provider_not_found", message="Provider not found", status_code=404)

        # Validate that all requested service_ids belong to the business
        if service_ids:
            matching_services = (
                self.db.execute(
                    select(Service.id).filter(Service.id.in_(service_ids), Service.business_id == business_id)
                )
                .scalars()
                .all()
            )

            if len(matching_services) != len(service_ids):
                raise DomainError(code="service_not_found", message="One or more services not found", status_code=404)

        try:
            # Delete existing assignments
            self.db.execute(delete(ProviderService).filter_by(business_id=business_id, provider_id=provider_id))

            # Insert new assignments
            for sid in service_ids:
                ps = ProviderService(
                    business_id=business_id,
                    provider_id=provider_id,
                    service_id=sid,
                )
                self.db.add(ps)

            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return AdminProviderServicesDetail(provider_id=provider_id, service_ids=service_ids)
