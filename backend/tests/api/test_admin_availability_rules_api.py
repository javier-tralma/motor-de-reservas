import threading
import uuid
from datetime import time

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.auth import hash_password
from app.core.config import settings
from app.models.admin_user import AdminUser
from app.models.availability import AvailabilityRule
from app.models.business import Business
from app.models.provider import Provider, ProviderService
from app.models.service import Service
from app.schemas.availability_admin import AdminAvailabilityRuleItem
from app.services.availability_admin_service import AvailabilityAdminService
from tests.conftest import engine as db_engine


def setup_rules_test_data(db: Session, monkeypatch=None):
    biz_id = uuid.uuid4()
    if monkeypatch:
        monkeypatch.setattr(settings, "BUSINESS_ID", str(biz_id))
    else:
        settings.BUSINESS_ID = str(biz_id)

    biz = Business(
        id=biz_id,
        name="Estudio Nómada",
        slug=f"estudio-nomada-{uuid.uuid4().hex[:6]}",
        timezone="America/Santiago",
        locale="es-CL",
        email="contacto@estudionomada.cl",
    )
    db.add(biz)
    db.commit()

    admin = AdminUser(
        business_id=biz_id,
        email="admin@estudionomada.cl",
        password_hash=hash_password("Password123!"),
        display_name="Javier",
        is_active=True,
    )
    db.add(admin)

    p1 = Provider(
        id=uuid.uuid4(),
        business_id=biz_id,
        name="Camila Rojas",
        email="camila@estudionomada.cl",
        is_active=True,
        sort_order=0,
    )
    p2_empty = Provider(
        id=uuid.uuid4(),
        business_id=biz_id,
        name="Gonzalo Valenzuela",
        email="gonzalo@estudionomada.cl",
        is_active=True,
        sort_order=1,
    )
    db.add_all([p1, p2_empty])

    # Initial rules for p1: Monday 09:00-13:00 and 14:00-18:00
    r1 = AvailabilityRule(
        id=uuid.uuid4(),
        business_id=biz_id,
        provider_id=p1.id,
        weekday=0,
        start_time=time(9, 0),
        end_time=time(13, 0),
    )
    r2 = AvailabilityRule(
        id=uuid.uuid4(),
        business_id=biz_id,
        provider_id=p1.id,
        weekday=0,
        start_time=time(14, 0),
        end_time=time(18, 0),
    )
    db.add_all([r1, r2])
    db.commit()

    # Other business
    other_biz_id = uuid.uuid4()
    other_biz = Business(
        id=other_biz_id,
        name="Otro Negocio",
        slug=f"otro-negocio-{uuid.uuid4().hex[:6]}",
        timezone="America/Santiago",
        locale="es-CL",
        email="otro@negocio.cl",
    )
    db.add(other_biz)
    db.commit()

    other_provider = Provider(
        id=uuid.uuid4(),
        business_id=other_biz_id,
        name="Proveedor Externo",
        is_active=True,
    )
    db.add(other_provider)
    db.commit()

    return biz, admin, p1, p2_empty, other_biz, other_provider


def test_admin_availability_rules_auth_and_csrf(client: TestClient, db_session: Session, monkeypatch):
    biz, admin, p1, p2_empty, other_biz, other_provider = setup_rules_test_data(db_session, monkeypatch)

    # 1. Unauthenticated GET -> 401
    res_unauth_get = client.get(f"/api/admin/providers/{p1.id}/availability-rules")
    assert res_unauth_get.status_code == 401

    # 2. Unauthenticated PUT -> 401
    res_unauth_put = client.put(
        f"/api/admin/providers/{p1.id}/availability-rules",
        json={"rules": []},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_unauth_put.status_code == 401

    # Login
    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    # 3. Authenticated PUT without Origin -> 403
    res_no_origin = client.put(
        f"/api/admin/providers/{p1.id}/availability-rules",
        json={"rules": []},
    )
    assert res_no_origin.status_code == 403

    # 4. Authenticated PUT with invalid Origin -> 403
    res_bad_origin = client.put(
        f"/api/admin/providers/{p1.id}/availability-rules",
        json={"rules": []},
        headers={"Origin": "https://attacker.com"},
    )
    assert res_bad_origin.status_code == 403


def test_admin_availability_rules_get_empty_populated_and_scoping(client: TestClient, db_session: Session, monkeypatch):
    biz, admin, p1, p2_empty, other_biz, other_provider = setup_rules_test_data(db_session, monkeypatch)

    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    # 1. GET populated rules (p1)
    res_p1 = client.get(f"/api/admin/providers/{p1.id}/availability-rules")
    assert res_p1.status_code == 200
    rules_p1 = res_p1.json()["data"]
    assert len(rules_p1) == 2
    assert rules_p1[0] == {"weekday": 0, "start_time": "09:00:00", "end_time": "13:00:00"}
    assert rules_p1[1] == {"weekday": 0, "start_time": "14:00:00", "end_time": "18:00:00"}

    # 2. GET empty rules (p2_empty)
    res_p2 = client.get(f"/api/admin/providers/{p2_empty.id}/availability-rules")
    assert res_p2.status_code == 200
    rules_p2 = res_p2.json()["data"]
    assert rules_p2 == []

    # 3. GET cross-tenant provider -> 404 provider_not_found
    res_other = client.get(f"/api/admin/providers/{other_provider.id}/availability-rules")
    assert res_other.status_code == 404
    assert res_other.json()["error"]["code"] == "provider_not_found"


def test_admin_availability_rules_put_validations_and_edge_cases(client: TestClient, db_session: Session, monkeypatch):
    biz, admin, p1, p2_empty, other_biz, other_provider = setup_rules_test_data(db_session, monkeypatch)

    client.post(
        "/api/admin/auth/login",
        json={"email": "admin@estudionomada.cl", "password": "Password123!"},
        headers={"Origin": settings.FRONTEND_URL},
    )

    # 1. Invalid start_time >= end_time -> 422
    for bad_order in [
        {"weekday": 0, "start_time": "13:00:00", "end_time": "09:00:00"},
        {"weekday": 0, "start_time": "10:00:00", "end_time": "10:00:00"},
    ]:
        res_bad_order = client.put(
            f"/api/admin/providers/{p1.id}/availability-rules",
            json={"rules": [bad_order]},
            headers={"Origin": settings.FRONTEND_URL},
        )
        assert res_bad_order.status_code == 422

    # 2. Overlapping intervals on same weekday -> 422 (e.g. 09:00-12:00 and 11:00-14:00)
    res_overlap = client.put(
        f"/api/admin/providers/{p1.id}/availability-rules",
        json={
            "rules": [
                {"weekday": 0, "start_time": "09:00:00", "end_time": "12:00:00"},
                {"weekday": 0, "start_time": "11:00:00", "end_time": "14:00:00"},
            ]
        },
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_overlap.status_code == 422

    # Verify original rules unchanged in DB
    db_rules = db_session.query(AvailabilityRule).filter_by(provider_id=p1.id).all()
    assert len(db_rules) == 2

    # 3. Invalid weekday (<0 or >6) -> 422
    for bad_w in [-1, 7]:
        res_bad_w = client.put(
            f"/api/admin/providers/{p1.id}/availability-rules",
            json={"rules": [{"weekday": bad_w, "start_time": "09:00:00", "end_time": "13:00:00"}]},
            headers={"Origin": settings.FRONTEND_URL},
        )
        assert res_bad_w.status_code == 422

    # 4. Extra fields (extra="forbid") -> 422
    res_extra = client.put(
        f"/api/admin/providers/{p1.id}/availability-rules",
        json={"rules": [{"weekday": 0, "start_time": "09:00:00", "end_time": "13:00:00", "extra_field": "invalid"}]},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_extra.status_code == 422

    # 5. Adjacency allowed in backend: 09:00-11:00 and 11:00-13:00 -> 200
    res_adj = client.put(
        f"/api/admin/providers/{p1.id}/availability-rules",
        json={
            "rules": [
                {"weekday": 0, "start_time": "09:00:00", "end_time": "11:00:00"},
                {"weekday": 0, "start_time": "11:00:00", "end_time": "13:00:00"},
            ]
        },
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_adj.status_code == 200
    adj_data = res_adj.json()["data"]
    assert len(adj_data) == 2

    # 6. Replacement with empty list [] -> 200 (clears all rules)
    res_clear = client.put(
        f"/api/admin/providers/{p1.id}/availability-rules",
        json={"rules": []},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_clear.status_code == 200
    assert res_clear.json()["data"] == []

    # 7. Cross-tenant provider PUT -> 404
    res_other_put = client.put(
        f"/api/admin/providers/{other_provider.id}/availability-rules",
        json={"rules": [{"weekday": 0, "start_time": "09:00:00", "end_time": "13:00:00"}]},
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert res_other_put.status_code == 404
    assert res_other_put.json()["error"]["code"] == "provider_not_found"


def test_concurrent_availability_rules_replacement_with_barrier():
    SessionMaker = sessionmaker(bind=db_engine)
    setup_session = SessionMaker()

    biz_id = None
    other_biz_id = None
    p1_id = None

    original_business_id = getattr(settings, "BUSINESS_ID", None)

    try:
        biz, admin, p1, p2_empty, other_biz, other_provider = setup_rules_test_data(setup_session)
        biz_id = biz.id
        other_biz_id = other_biz.id
        p1_id = p1.id

        barrier = threading.Barrier(2, timeout=5.0)
        results = [None, None]
        exceptions = [None, None]

        payload_a = [
            AdminAvailabilityRuleItem(weekday=0, start_time=time(9, 0), end_time=time(13, 0)),
            AdminAvailabilityRuleItem(weekday=0, start_time=time(14, 0), end_time=time(18, 0)),
        ]
        payload_b = [
            AdminAvailabilityRuleItem(weekday=1, start_time=time(10, 0), end_time=time(17, 0)),
        ]

        def worker(thread_idx, rules):
            session = SessionMaker()
            try:
                avail_svc = AvailabilityAdminService(session)

                # Wait at barrier immediately before calling replace and taking the FOR UPDATE lock
                barrier.wait()

                res = avail_svc.replace_provider_availability_rules(
                    business_id=biz_id,
                    provider_id=p1_id,
                    rules=rules,
                )
                results[thread_idx] = res
            except Exception as e:
                exceptions[thread_idx] = e
            finally:
                session.close()

        t1 = threading.Thread(target=worker, args=(0, payload_a))
        t2 = threading.Thread(target=worker, args=(1, payload_b))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Both operations succeed cleanly
        assert exceptions[0] is None, f"Thread 0 failed with {exceptions[0]}"
        assert exceptions[1] is None, f"Thread 1 failed with {exceptions[1]}"
        assert results[0] is not None
        assert results[1] is not None

        # Verify final DB state is EXACTLY equal to payload_a or payload_b (never union, mix or duplicates)
        verify_session = SessionMaker()
        try:
            db_rules = (
                verify_session.query(AvailabilityRule)
                .filter_by(business_id=biz_id, provider_id=p1_id)
                .order_by(AvailabilityRule.weekday.asc(), AvailabilityRule.start_time.asc())
                .all()
            )
            final_tuples = [(r.weekday, r.start_time, r.end_time) for r in db_rules]
            expected_a = [(r.weekday, r.start_time, r.end_time) for r in payload_a]
            expected_b = [(r.weekday, r.start_time, r.end_time) for r in payload_b]

            assert (final_tuples == expected_a) or (final_tuples == expected_b), (
                f"Final DB state must be exactly Payload A or Payload B, got {final_tuples}"
            )
        finally:
            verify_session.close()

    finally:
        setattr(settings, "BUSINESS_ID", original_business_id)

        if biz_id or other_biz_id:
            cleanup_session = SessionMaker()
            try:
                biz_ids = [bid for bid in (biz_id, other_biz_id) if bid]
                cleanup_session.query(AvailabilityRule).filter(AvailabilityRule.business_id.in_(biz_ids)).delete()
                cleanup_session.query(ProviderService).filter(ProviderService.business_id.in_(biz_ids)).delete()
                cleanup_session.query(Provider).filter(Provider.business_id.in_(biz_ids)).delete()
                cleanup_session.query(Service).filter(Service.business_id.in_(biz_ids)).delete()
                cleanup_session.query(AdminUser).filter(AdminUser.business_id.in_(biz_ids)).delete()
                cleanup_session.query(Business).filter(Business.id.in_(biz_ids)).delete()
                cleanup_session.commit()
            except Exception:
                cleanup_session.rollback()
            finally:
                cleanup_session.close()
        setup_session.close()
