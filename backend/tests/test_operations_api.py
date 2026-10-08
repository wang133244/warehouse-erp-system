"""收货加库存、出库预留与完成。"""

from collections.abc import Generator  # from collections.abc imp

import pytest  # import pytest
from fastapi.testclient import TestClient  # from fastapi.testclient 
from sqlalchemy import create_engine  # from sqlalchemy import c
from sqlalchemy.orm import Session, sessionmaker  # from sqlalchemy.orm impo

from backend.app.core.security import hash_password  # from backend.app.core.se
from backend.app.db.base import Base  # from backend.app.db.base
from backend.app.models import Product, Role, StockBalance, UserAccount, UserRole, UserWarehouseScope, Warehouse, WarehouseLocation  # from backend.app.models 
from backend.app.db.session import get_db  # from backend.app.db.sess
from backend.app.main import create_app  # from backend.app.main im


@pytest.fixture  # @pytest.fixture
def client() -> Generator[TestClient, None, None]:  # def client() -> Generato
    engine = create_engine(  # engine = create_engine(
        "sqlite+pysqlite:///:memory:",  # 'sqlite+pysqlite:///:mem
        connect_args={"check_same_thread": False},  # connect_args={'check_sam
        poolclass=__import__("sqlalchemy").pool.StaticPool,  # poolclass=__import__('sq
    )  # )
    Base.metadata.create_all(engine)  # Base.metadata.create_all
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)  # SessionLocal = sessionma
    with SessionLocal() as db:  # with SessionLocal() as d
        role = Role(role_code="warehouse_manager", role_name="仓库管理员")  # role = Role(role_code='w
        user = UserAccount(username="operator", password_hash=hash_password("password"), display_name="操作员")  # user = UserAccount(usern
        warehouse = Warehouse(warehouse_code="WH-01", warehouse_name="一号仓")  # warehouse = Warehouse(wa
        db.add_all([role, user, warehouse]); db.flush()  # db.add_all([role, user, 
        db.add(UserRole(user_id=user.user_id, role_id=role.role_id))  # db.add(UserRole(user_id=
        db.add(UserWarehouseScope(user_id=user.user_id, warehouse_id=warehouse.warehouse_id))  # db.add(UserWarehouseScop
        location = WarehouseLocation(warehouse_id=warehouse.warehouse_id, location_code="A-01", zone_code="A", aisle_code="01", rack_code="01", position_code="01")  # location = WarehouseLoca
        product = Product(sku_code="SKU-1", source_product_code="SRC-1", brand="品牌", product_name="商品", category="分类", size="标准", function_feature="普通", color="蓝", pallet_spec="箱", pallet_capacity=10)  # product = Product(sku_co
        db.add_all([location, product]); db.flush()  # db.add_all([location, pr
        db.add(StockBalance(product_id=product.product_id, location_id=location.location_id, quantity=10, reserved_quantity=0))  # db.add(StockBalance(prod
        db.commit()  # db.commit()

    app = create_app()  # app = create_app()
    def override_get_db() -> Generator[Session, None, None]:  # def override_get_db() ->
        with SessionLocal() as db:  # with SessionLocal() as d
            yield db  # yield db
    app.dependency_overrides[get_db] = override_get_db  # app.dependency_overrides
    with TestClient(app) as test_client:  # with TestClient(app) as 
        yield test_client  # yield test_client


def _headers(client: TestClient, key: str | None = None) -> dict[str, str]:  # def _headers(client: Tes
    login = client.post("/api/v1/auth/login", json={"username": "operator", "password": "password"})  # login = client.post('/ap
    token = login.json()["access_token"]  # token = login.json()['ac
    headers = {"Authorization": f"Bearer {token}"}  # headers = {'Authorizatio
    if key:  # if key:
        headers["Idempotency-Key"] = key  # headers['Idempotency-Key
    return headers  # return headers


def test_inbound_and_outbound_close_inventory_loop(client: TestClient):  # def test_inbound_and_out
    created = client.post("/api/v1/inbounds", headers=_headers(client, "inbound-create"), json={"order_no": "IN-001", "items": [{"product_id": 1, "location_id": 1, "quantity": 5}]})  # created = client.post('/
    assert created.status_code == 201  # assert created.status_co
    inbound_id = created.json()["inbound_order_id"]  # inbound_id = created.jso

    confirmed = client.post(f"/api/v1/inbounds/{inbound_id}/confirm", headers=_headers(client, "inbound-confirm"))  # confirmed = client.post(
    assert confirmed.status_code == 200  # assert confirmed.status_
    assert client.get("/api/v1/inventory/1/availability", headers=_headers(client)).json()["quantity"] == 15  # assert client.get('/api/

    outbound = client.post("/api/v1/outbounds", headers=_headers(client, "outbound-create"), json={"order_no": "OUT-001", "items": [{"product_id": 1, "quantity": 3}]})  # outbound = client.post('
    assert outbound.status_code == 201  # assert outbound.status_c
    outbound_id = outbound.json()["outbound_order_id"]  # outbound_id = outbound.j
    allocated = client.post(f"/api/v1/outbounds/{outbound_id}/allocate", headers=_headers(client, "outbound-allocate"))  # allocated = client.post(
    assert allocated.status_code == 200  # assert allocated.status_
    task_id = allocated.json()["tasks"][0]["picking_task_id"]  # task_id = allocated.json
    assert client.get("/api/v1/inventory/1/availability", headers=_headers(client)).json()["available_quantity"] == 12  # assert client.get('/api/

    picked = client.post(f"/api/v1/picking-tasks/{task_id}/confirm", headers=_headers(client, "task-confirm"))  # picked = client.post(f'/
    assert picked.status_code == 200  # assert picked.status_cod
    assert picked.json()["order_status"] == "picked"  # assert picked.json()['or
    blocked = client.post(f"/api/v1/outbounds/{outbound_id}/complete", headers=_headers(client, "outbound-complete-early"))  # blocked = client.post(f'
    assert blocked.status_code == 409  # assert blocked.status_co
    reviewed = client.post(  # reviewed = client.post(
        f"/api/v1/outbounds/{outbound_id}/review",  # f'/api/v1/outbounds/{out
        headers=_headers(client, "outbound-review"),  # headers=_headers(client,
        json={"comment": "数量与客户信息已核对"},  # json={'comment': '数量与客户信
    )  # )
    assert reviewed.status_code == 200  # assert reviewed.status_c
    assert reviewed.json()["status"] == "reviewed"  # assert reviewed.json()['
    completed = client.post(f"/api/v1/outbounds/{outbound_id}/complete", headers=_headers(client, "outbound-complete"))  # completed = client.post(
    assert completed.status_code == 200  # assert completed.status_
    final = client.get("/api/v1/inventory/1/availability", headers=_headers(client)).json()  # final = client.get('/api
    assert final["quantity"] == 12  # assert final['quantity']
    assert final["reserved_quantity"] == 0  # assert final['reserved_q


def test_catalog_inventory_and_inbound_keyword_search(client: TestClient):  # def test_catalog_invento
    headers = _headers(client, "inbound-search-create")  # headers = _headers(clien
    created = client.post(  # created = client.post(
        "/api/v1/inbounds",  # '/api/v1/inbounds',
        headers=headers,  # headers=headers,
        json={"order_no": "IN-SEARCH-9", "items": [{"product_id": 1, "location_id": 1, "quantity": 2}]},  # json={'order_no': 'IN-SE
    )  # )
    assert created.status_code == 201  # assert created.status_co

    token_headers = _headers(client)  # token_headers = _headers
    locations = client.get("/api/v1/locations?keyword=A-01", headers=token_headers)  # locations = client.get('
    assert locations.status_code == 200  # assert locations.status_
    assert locations.json()["total"] == 1  # assert locations.json()[
    assert locations.json()["items"][0]["location_code"] == "A-01"  # assert locations.json()[

    missing_locations = client.get("/api/v1/locations?keyword=NO-SUCH-BIN", headers=token_headers)  # missing_locations = clie
    assert missing_locations.json()["total"] == 0  # assert missing_locations

    balances = client.get("/api/v1/inventory/balances?keyword=SKU-1", headers=token_headers)  # balances = client.get('/
    assert balances.status_code == 200  # assert balances.status_c
    assert balances.json()["total"] == 1  # assert balances.json()['

    inbounds = client.get("/api/v1/inbounds?keyword=IN-SEARCH-9&status=draft", headers=token_headers)  # inbounds = client.get('/
    assert inbounds.status_code == 200  # assert inbounds.status_c
    assert inbounds.json()["total"] == 1  # assert inbounds.json()['
    assert inbounds.json()["items"][0]["order_no"] == "IN-SEARCH-9"  # assert inbounds.json()['
    assert inbounds.json()["items"][0]["username"] == "operator"  # assert inbounds.json()['

    logs = client.get("/api/v1/audit-logs", headers=token_headers)  # logs = client.get('/api/
    assert logs.status_code == 200  # assert logs.status_code 
    assert logs.json()["items"]  # assert logs.json()['item
    assert logs.json()["items"][0]["username"] == "operator"  # assert logs.json()['item

    hidden = client.get("/api/v1/inbounds?keyword=IN-SEARCH-9&status=confirmed", headers=token_headers)  # hidden = client.get('/ap
    assert hidden.json()["total"] == 0  # assert hidden.json()['to


def test_write_endpoints_require_idempotency_key(client: TestClient):  # def test_write_endpoints
    response = client.post("/api/v1/inbounds", headers=_headers(client), json={"order_no": "IN-MISSING", "items": [{"product_id": 1, "location_id": 1, "quantity": 1}]})  # response = client.post('
    assert response.status_code == 400  # assert response.status_c
    assert response.json()["code"] == "IDEMPOTENCY_KEY_REQUIRED"  # assert response.json()['
