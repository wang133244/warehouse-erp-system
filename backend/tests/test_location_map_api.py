"""库位分区结构。"""

from collections.abc import Generator  # from collections.abc imp

import pytest  # import pytest
from fastapi import FastAPI  # from fastapi import Fast
from fastapi.testclient import TestClient  # from fastapi.testclient 
from sqlalchemy import create_engine  # from sqlalchemy import c
from sqlalchemy.orm import Session, sessionmaker  # from sqlalchemy.orm impo

from backend.app.controllers.auth import router as auth_router  # from backend.app.control
from backend.app.controllers.catalog import router as catalog_router  # from backend.app.control
from backend.app.core.security import hash_password  # from backend.app.core.se
from backend.app.db.base import Base  # from backend.app.db.base
from backend.app.models import Role, UserAccount, UserRole, Warehouse, WarehouseLocation  # from backend.app.models 
from backend.app.db.session import get_db  # from backend.app.db.sess


@pytest.fixture  # @pytest.fixture
def client() -> Generator[TestClient, None, None]:  # def client() -> Generato
    engine = create_engine(  # engine = create_engine(
        "sqlite+pysqlite:///:memory:",  # 'sqlite+pysqlite:///:mem
        connect_args={"check_same_thread": False},  # connect_args={'check_sam
        poolclass=__import__("sqlalchemy").pool.StaticPool,  # poolclass=__import__('sq
    )  # )
    Base.metadata.create_all(engine)  # Base.metadata.create_all
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)  # TestingSessionLocal = se

    with TestingSessionLocal() as db:  # with TestingSessionLocal
        role = Role(role_code="warehouse_manager", role_name="仓库管理员")  # role = Role(role_code='w
        db.add(role)  # db.add(role)
        db.flush()  # db.flush()
        user = UserAccount(  # user = UserAccount(
            username="alice",  # username='alice',
            password_hash=hash_password("correct-password"),  # password_hash=hash_passw
            display_name="Alice",  # display_name='Alice',
            is_active=True,  # is_active=True,
        )  # )
        db.add(user)  # db.add(user)
        db.flush()  # db.flush()
        db.add(UserRole(user_id=user.user_id, role_id=role.role_id))  # db.add(UserRole(user_id=
        warehouse = Warehouse(warehouse_code="MEGA", warehouse_name="Mega Star 配送中心")  # warehouse = Warehouse(wa
        db.add(warehouse)  # db.add(warehouse)
        db.flush()  # db.flush()
        for code, zone in (("AF01A", "A"), ("AF01B", "A"), ("BF01A", "B"), ("CF01A", "C"), ("DF01A", "D")):  # for code, zone in (('AF0
            db.add(  # db.add(
                WarehouseLocation(  # WarehouseLocation(
                    warehouse_id=warehouse.warehouse_id,  # warehouse_id=warehouse.w
                    location_code=code,  # location_code=code,
                    zone_code=zone,  # zone_code=zone,
                    aisle_code=code[:2],  # aisle_code=code[:2],
                    rack_code=code[:4],  # rack_code=code[:4],
                    position_code=code[4],  # position_code=code[4],
                )  # )
            )  # )
        db.commit()  # db.commit()

    app = FastAPI()  # app = FastAPI()
    app.include_router(auth_router, prefix="/api/v1")  # app.include_router(auth_
    app.include_router(catalog_router, prefix="/api/v1")  # app.include_router(catal

    def override_get_db() -> Generator[Session, None, None]:  # def override_get_db() ->
        with TestingSessionLocal() as db:  # with TestingSessionLocal
            yield db  # yield db

    app.dependency_overrides[get_db] = override_get_db  # app.dependency_overrides
    with TestClient(app) as test_client:  # with TestClient(app) as 
        yield test_client  # yield test_client


def login(client: TestClient) -> str:  # def login(client: TestCl
    response = client.post("/api/v1/auth/login", json={"username": "alice", "password": "correct-password"})  # response = client.post('
    assert response.status_code == 200  # assert response.status_c
    return response.json()["access_token"]  # return response.json()['


def test_location_map_returns_all_zones_not_just_first_page(client: TestClient):  # def test_location_map_re
    headers = {"Authorization": f"Bearer {login(client)}"}  # headers = {'Authorizatio
    first_page = client.get("/api/v1/locations?limit=2", headers=headers)  # first_page = client.get(
    assert first_page.status_code == 200  # assert first_page.status
    assert first_page.json()["total"] == 5  # assert first_page.json()
    assert {item["zone_code"] for item in first_page.json()["items"]} == {"A"}  # assert {item['zone_code'

    mapped = client.get("/api/v1/locations/map", headers=headers)  # mapped = client.get('/ap
    assert mapped.status_code == 200  # assert mapped.status_cod
    body = mapped.json()  # body = mapped.json()
    assert body["total"] == 5  # assert body['total'] == 
    zones = {item["zone_code"]: item for item in body["items"]}  # zones = {item['zone_code
    assert set(zones) == {"A", "B", "C", "D"}  # assert set(zones) == {'A
    assert zones["A"]["location_codes"] == ["AF01A", "AF01B"]  # assert zones['A']['locat
    assert zones["C"]["warehouse_code"] == "MEGA"  # assert zones['C']['wareh
    assert zones["C"]["location_codes"] == ["CF01A"]  # assert zones['C']['locat
    assert zones["D"]["location_codes"] == ["DF01A"]  # assert zones['D']['locat


def test_list_locations_can_filter_by_zone(client: TestClient):  # def test_list_locations_
    headers = {"Authorization": f"Bearer {login(client)}"}  # headers = {'Authorizatio
    response = client.get("/api/v1/locations?zone_code=C", headers=headers)  # response = client.get('/
    assert response.status_code == 200  # assert response.status_c
    assert response.json()["total"] == 1  # assert response.json()['
    assert response.json()["items"][0]["location_code"] == "CF01A"  # assert response.json()['
