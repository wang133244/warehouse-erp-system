from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.catalog import router as catalog_router
from backend.app.core.security import hash_password
from backend.app.db.base import Base
from backend.app.db.models import (
    DataImportBatch,
    Product,
    Role,
    UserAccount,
    UserRole,
    Warehouse,
    WarehouseLocation,
)
from backend.app.db.session import get_db


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=__import__("sqlalchemy").pool.StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with TestingSessionLocal() as db:
        role = Role(role_code="warehouse_manager", role_name="仓库管理员")
        db.add(role)
        db.flush()
        user = UserAccount(
            username="alice",
            password_hash=hash_password("correct-password"),
            display_name="Alice",
            is_active=True,
        )
        db.add(user)
        db.flush()
        db.add(UserRole(user_id=user.user_id, role_id=role.role_id))
        warehouse = Warehouse(warehouse_code="WH-01", warehouse_name="一号仓")
        db.add(warehouse)
        db.flush()
        db.add(
            WarehouseLocation(
                warehouse_id=warehouse.warehouse_id,
                location_code="A-01-01-01",
                zone_code="A",
                aisle_code="01",
                rack_code="01",
                position_code="01",
            )
        )
        db.add(
            Product(
                sku_code="SKU-001",
                source_product_code="SRC-001",
                brand="品牌A",
                product_name="测试商品",
                category="测试",
                size="标准",
                function_feature="普通",
                color="蓝",
                pallet_spec="箱",
                pallet_capacity=10,
            )
        )
        db.add(
            DataImportBatch(
                batch_no="BATCH-001",
                dataset_name="库存初始化",
                dataset_version="1.0",
                total_rows=10,
                valid_rows=10,
                invalid_rows=0,
                status="success",
            )
        )
        db.commit()

    app = FastAPI()
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(catalog_router, prefix="/api/v1")

    def override_get_db() -> Generator[Session, None, None]:
        with TestingSessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "correct-password"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_login_me_and_catalog_queries_use_jwt_and_rbac(client: TestClient):
    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["username"] == "alice"
    assert me.json()["roles"] == ["warehouse_manager"]

    products = client.get("/api/v1/products?keyword=测试", headers=headers)
    assert products.status_code == 200
    assert products.json()["total"] == 1
    assert products.json()["items"][0]["sku_code"] == "SKU-001"

    warehouses = client.get("/api/v1/warehouses", headers=headers)
    assert warehouses.status_code == 200
    assert warehouses.json()["items"][0]["warehouse_code"] == "WH-01"

    locations = client.get("/api/v1/locations?warehouse_id=1", headers=headers)
    assert locations.status_code == 200
    assert locations.json()["items"][0]["location_code"] == "A-01-01-01"

    imports = client.get("/api/v1/imports", headers=headers)
    assert imports.status_code == 200
    assert imports.json()["items"][0]["batch_no"] == "BATCH-001"


def test_login_rejects_invalid_credentials_and_catalog_requires_auth(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "用户名或密码错误"

    unauthenticated = client.get("/api/v1/products")
    assert unauthenticated.status_code == 401


def test_invalid_token_is_rejected(client: TestClient):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    assert response.status_code == 401
