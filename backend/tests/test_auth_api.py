"""登录登出与无 token。"""

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
from backend.app.models import (  # from backend.app.models 
    DataImportBatch,  # DataImportBatch,
    Product,  # Product,
    Role,  # Role,
    UserAccount,  # UserAccount,
    UserRole,  # UserRole,
    Warehouse,  # Warehouse,
    WarehouseLocation,  # WarehouseLocation,
)  # )
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
        warehouse = Warehouse(warehouse_code="WH-01", warehouse_name="一号仓")  # warehouse = Warehouse(wa
        db.add(warehouse)  # db.add(warehouse)
        db.flush()  # db.flush()
        db.add(  # db.add(
            WarehouseLocation(  # WarehouseLocation(
                warehouse_id=warehouse.warehouse_id,  # warehouse_id=warehouse.w
                location_code="A-01-01-01",  # location_code='A-01-01-0
                zone_code="A",  # zone_code='A',
                aisle_code="01",  # aisle_code='01',
                rack_code="01",  # rack_code='01',
                position_code="01",  # position_code='01',
            )  # )
        )  # )
        db.add(  # db.add(
            Product(  # Product(
                sku_code="SKU-001",  # sku_code='SKU-001',
                source_product_code="SRC-001",  # source_product_code='SRC
                brand="品牌A",  # brand='品牌A',
                product_name="测试商品",  # product_name='测试商品',
                category="测试",  # category='测试',
                size="标准",  # size='标准',
                function_feature="普通",  # function_feature='普通',
                color="蓝",  # color='蓝',
                pallet_spec="箱",  # pallet_spec='箱',
                pallet_capacity=10,  # pallet_capacity=10,
            )  # )
        )  # )
        db.add(  # db.add(
            DataImportBatch(  # DataImportBatch(
                batch_no="BATCH-001",  # batch_no='BATCH-001',
                dataset_name="库存初始化",  # dataset_name='库存初始化',
                dataset_version="1.0",  # dataset_version='1.0',
                total_rows=10,  # total_rows=10,
                valid_rows=10,  # valid_rows=10,
                invalid_rows=0,  # invalid_rows=0,
                status="success",  # status='success',
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
    response = client.post(  # response = client.post(
        "/api/v1/auth/login",  # '/api/v1/auth/login',
        json={"username": "alice", "password": "correct-password"},  # json={'username': 'alice
    )  # )
    assert response.status_code == 200  # assert response.status_c
    return response.json()["access_token"]  # return response.json()['


def test_login_me_and_catalog_queries_use_jwt_and_rbac(client: TestClient):  # def test_login_me_and_ca
    token = login(client)  # token = login(client)
    headers = {"Authorization": f"Bearer {token}"}  # headers = {'Authorizatio

    me = client.get("/api/v1/auth/me", headers=headers)  # me = client.get('/api/v1
    assert me.status_code == 200  # assert me.status_code ==
    assert me.json()["username"] == "alice"  # assert me.json()['userna
    assert me.json()["roles"] == ["warehouse_manager"]  # assert me.json()['roles'

    products = client.get("/api/v1/products?keyword=测试", headers=headers)  # products = client.get('/
    assert products.status_code == 200  # assert products.status_c
    assert products.json()["total"] == 1  # assert products.json()['
    assert products.json()["items"][0]["sku_code"] == "SKU-001"  # assert products.json()['

    warehouses = client.get("/api/v1/warehouses", headers=headers)  # warehouses = client.get(
    assert warehouses.status_code == 200  # assert warehouses.status
    assert warehouses.json()["items"][0]["warehouse_code"] == "WH-01"  # assert warehouses.json()

    locations = client.get("/api/v1/locations?warehouse_id=1", headers=headers)  # locations = client.get('
    assert locations.status_code == 200  # assert locations.status_
    assert locations.json()["items"][0]["location_code"] == "A-01-01-01"  # assert locations.json()[

    imports = client.get("/api/v1/imports", headers=headers)  # imports = client.get('/a
    assert imports.status_code == 200  # assert imports.status_co
    assert imports.json()["items"][0]["batch_no"] == "BATCH-001"  # assert imports.json()['i


def test_login_rejects_invalid_credentials_and_catalog_requires_auth(client: TestClient):  # def test_login_rejects_i
    response = client.post(  # response = client.post(
        "/api/v1/auth/login",  # '/api/v1/auth/login',
        json={"username": "alice", "password": "wrong-password"},  # json={'username': 'alice
    )  # )
    assert response.status_code == 401  # assert response.status_c
    assert response.json()["detail"] == "用户名或密码错误"  # assert response.json()['

    unauthenticated = client.get("/api/v1/products")  # unauthenticated = client
    assert unauthenticated.status_code == 401  # assert unauthenticated.s


def test_invalid_token_is_rejected(client: TestClient):  # def test_invalid_token_i
    response = client.get(  # response = client.get(
        "/api/v1/auth/me",  # '/api/v1/auth/me',
        headers={"Authorization": "Bearer not-a-jwt"},  # headers={'Authorization'
    )  # )
    assert response.status_code == 401  # assert response.status_c


def test_logout_revokes_access_token(client: TestClient):  # def test_logout_revokes_
    from backend.app.core.cache import reset_cache  # from backend.app.core.ca

    reset_cache()  # reset_cache()
    token = login(client)  # token = login(client)
    headers = {"Authorization": f"Bearer {token}"}  # headers = {'Authorizatio
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200  # assert client.get('/api/
    logout = client.post("/api/v1/auth/logout", headers=headers)  # logout = client.post('/a
    assert logout.status_code == 204  # assert logout.status_cod
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401  # assert client.get('/api/
