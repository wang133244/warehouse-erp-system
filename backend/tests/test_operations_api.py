from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.security import hash_password
from backend.app.db.base import Base
from backend.app.db.models import Product, Role, StockBalance, UserAccount, UserRole, Warehouse, WarehouseLocation
from backend.app.db.session import get_db
from backend.app.main import create_app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=__import__("sqlalchemy").pool.StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db:
        role = Role(role_code="warehouse_manager", role_name="仓库管理员")
        user = UserAccount(username="operator", password_hash=hash_password("password"), display_name="操作员")
        warehouse = Warehouse(warehouse_code="WH-01", warehouse_name="一号仓")
        db.add_all([role, user, warehouse]); db.flush()
        db.add(UserRole(user_id=user.user_id, role_id=role.role_id))
        location = WarehouseLocation(warehouse_id=warehouse.warehouse_id, location_code="A-01", zone_code="A", aisle_code="01", rack_code="01", position_code="01")
        product = Product(sku_code="SKU-1", source_product_code="SRC-1", brand="品牌", product_name="商品", category="分类", size="标准", function_feature="普通", color="蓝", pallet_spec="箱", pallet_capacity=10)
        db.add_all([location, product]); db.flush()
        db.add(StockBalance(product_id=product.product_id, location_id=location.location_id, quantity=10, reserved_quantity=0))
        db.commit()

    app = create_app()
    def override_get_db() -> Generator[Session, None, None]:
        with SessionLocal() as db:
            yield db
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


def _headers(client: TestClient, key: str | None = None) -> dict[str, str]:
    login = client.post("/api/v1/auth/login", json={"username": "operator", "password": "password"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    if key:
        headers["Idempotency-Key"] = key
    return headers


def test_inbound_and_outbound_close_inventory_loop(client: TestClient):
    created = client.post("/api/v1/inbounds", headers=_headers(client, "inbound-create"), json={"order_no": "IN-001", "items": [{"product_id": 1, "location_id": 1, "quantity": 5}]})
    assert created.status_code == 201
    inbound_id = created.json()["inbound_order_id"]

    confirmed = client.post(f"/api/v1/inbounds/{inbound_id}/confirm", headers=_headers(client, "inbound-confirm"))
    assert confirmed.status_code == 200
    assert client.get("/api/v1/inventory/1/availability", headers=_headers(client)).json()["quantity"] == 15

    outbound = client.post("/api/v1/outbounds", headers=_headers(client, "outbound-create"), json={"order_no": "OUT-001", "items": [{"product_id": 1, "quantity": 3}]})
    assert outbound.status_code == 201
    outbound_id = outbound.json()["outbound_order_id"]
    allocated = client.post(f"/api/v1/outbounds/{outbound_id}/allocate", headers=_headers(client, "outbound-allocate"))
    assert allocated.status_code == 200
    task_id = allocated.json()["tasks"][0]["picking_task_id"]
    assert client.get("/api/v1/inventory/1/availability", headers=_headers(client)).json()["available_quantity"] == 12

    assert client.post(f"/api/v1/picking-tasks/{task_id}/confirm", headers=_headers(client, "task-confirm")).status_code == 200
    completed = client.post(f"/api/v1/outbounds/{outbound_id}/complete", headers=_headers(client, "outbound-complete"))
    assert completed.status_code == 200
    final = client.get("/api/v1/inventory/1/availability", headers=_headers(client)).json()
    assert final["quantity"] == 12
    assert final["reserved_quantity"] == 0


def test_write_endpoints_require_idempotency_key(client: TestClient):
    response = client.post("/api/v1/inbounds", headers=_headers(client), json={"order_no": "IN-MISSING", "items": [{"product_id": 1, "location_id": 1, "quantity": 1}]})
    assert response.status_code == 400
    assert response.json()["code"] == "IDEMPOTENCY_KEY_REQUIRED"
