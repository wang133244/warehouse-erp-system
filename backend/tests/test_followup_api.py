"""助手隔离、问候、历史 SKU、草稿不改库存。"""

from collections.abc import Generator  # from collections.abc imp

import pytest  # import pytest
from fastapi.testclient import TestClient  # from fastapi.testclient 
from sqlalchemy import create_engine, select  # from sqlalchemy import c
from sqlalchemy.orm import Session, sessionmaker  # from sqlalchemy.orm impo

from backend.app.core.security import hash_password  # from backend.app.core.se
from backend.app.db.base import Base  # from backend.app.db.base
from backend.app.models import (  # from backend.app.models 
    DataImportBatch,  # DataImportBatch,
    Product,  # Product,
    Role,  # Role,
    StockBalance,  # StockBalance,
    UserAccount,  # UserAccount,
    UserRole,  # UserRole,
    UserWarehouseScope,  # UserWarehouseScope,
    Warehouse,  # Warehouse,
    WarehouseLocation,  # WarehouseLocation,
)  # )
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
        admin_role = Role(role_code="admin", role_name="系统管理员")  # admin_role = Role(role_c
        manager_role = Role(role_code="warehouse_manager", role_name="仓库管理员")  # manager_role = Role(role
        operator_role = Role(role_code="warehouse_operator", role_name="仓库操作员")  # operator_role = Role(rol
        viewer_role = Role(role_code="viewer", role_name="只读查看者")  # viewer_role = Role(role_
        admin = UserAccount(username="admin", password_hash=hash_password("password"), display_name="管理员")  # admin = UserAccount(user
        operator = UserAccount(username="operator", password_hash=hash_password("password"), display_name="操作员")  # operator = UserAccount(u
        warehouse = Warehouse(warehouse_code="WH-01", warehouse_name="一号仓")  # warehouse = Warehouse(wa
        warehouse_two = Warehouse(warehouse_code="WH-02", warehouse_name="二号仓")  # warehouse_two = Warehous
        db.add_all(  # db.add_all(
            [admin_role, manager_role, operator_role, viewer_role, admin, operator, warehouse, warehouse_two]  # [admin_role, manager_rol
        )  # )
        db.flush()  # db.flush()
        db.add_all(  # db.add_all(
            [  # [
                UserRole(user_id=admin.user_id, role_id=admin_role.role_id),  # UserRole(user_id=admin.u
                UserRole(user_id=operator.user_id, role_id=operator_role.role_id),  # UserRole(user_id=operato
                UserWarehouseScope(user_id=operator.user_id, warehouse_id=warehouse.warehouse_id),  # UserWarehouseScope(user_
            ]  # ]
        )  # )
        location = WarehouseLocation(  # location = WarehouseLoca
            warehouse_id=warehouse.warehouse_id,  # warehouse_id=warehouse.w
            location_code="A-01",  # location_code='A-01',
            zone_code="A",  # zone_code='A',
            aisle_code="01",  # aisle_code='01',
            rack_code="01",  # rack_code='01',
            position_code="01",  # position_code='01',
        )  # )
        location_two = WarehouseLocation(  # location_two = Warehouse
            warehouse_id=warehouse_two.warehouse_id,  # warehouse_id=warehouse_t
            location_code="C-01",  # location_code='C-01',
            zone_code="B",  # zone_code='B',
            aisle_code="01",  # aisle_code='01',
            rack_code="01",  # rack_code='01',
            position_code="01",  # position_code='01',
        )  # )
        product = Product(  # product = Product(
            sku_code="SKU-1",  # sku_code='SKU-1',
            source_product_code="SRC-1",  # source_product_code='SRC
            brand="品牌",  # brand='品牌',
            product_name="商品",  # product_name='商品',
            category="分类",  # category='分类',
            size="标准",  # size='标准',
            function_feature="普通",  # function_feature='普通',
            color="蓝",  # color='蓝',
            pallet_spec="箱",  # pallet_spec='箱',
            pallet_capacity=10,  # pallet_capacity=10,
        )  # )
        db.add_all([location, location_two, product])  # db.add_all([location, lo
        db.flush()  # db.flush()
        db.add(StockBalance(product_id=product.product_id, location_id=location.location_id, quantity=4, reserved_quantity=0))  # db.add(StockBalance(prod
        db.add(  # db.add(
            DataImportBatch(  # DataImportBatch(
                batch_no="IMP-001",  # batch_no='IMP-001',
                dataset_name="mega_star_inbound",  # dataset_name='mega_star_
                dataset_version="v1",  # dataset_version='v1',
                total_rows=10,  # total_rows=10,
                valid_rows=8,  # valid_rows=8,
                invalid_rows=2,  # invalid_rows=2,
                status="imported",  # status='imported',
                notes="2 行库位编码无法匹配",  # notes='2 行库位编码无法匹配',
            )  # )
        )  # )
        db.commit()  # db.commit()

    app = create_app()  # app = create_app()

    def override_get_db() -> Generator[Session, None, None]:  # def override_get_db() ->
        with SessionLocal() as db:  # with SessionLocal() as d
            yield db  # yield db

    app.dependency_overrides[get_db] = override_get_db  # app.dependency_overrides
    with TestClient(app) as test_client:  # with TestClient(app) as 
        yield test_client  # yield test_client


def _headers(client: TestClient, username: str = "admin", key: str | None = None) -> dict[str, str]:  # def _headers(client: Tes
    login = client.post("/api/v1/auth/login", json={"username": username, "password": "password"})  # login = client.post('/ap
    token = login.json()["access_token"]  # token = login.json()['ac
    headers = {"Authorization": f"Bearer {token}"}  # headers = {'Authorizatio
    if key:  # if key:
        headers["Idempotency-Key"] = key  # headers['Idempotency-Key
    return headers  # return headers


def test_receiving_lists_drafts_and_confirms_with_received_quantity(client: TestClient):  # def test_receiving_lists
    created = client.post(  # created = client.post(
        "/api/v1/inbounds",  # '/api/v1/inbounds',
        headers=_headers(client, "operator", "in-create"),  # headers=_headers(client,
        json={"order_no": "IN-R-1", "items": [{"product_id": 1, "location_id": 1, "quantity": 5}]},  # json={'order_no': 'IN-R-
    )  # )
    assert created.status_code == 201  # assert created.status_co
    inbound_id = created.json()["inbound_order_id"]  # inbound_id = created.jso
    queue = client.get("/api/v1/receivings", headers=_headers(client, "operator"))  # queue = client.get('/api
    assert queue.status_code == 200  # assert queue.status_code
    assert queue.json()["total"] == 1  # assert queue.json()['tot
    assert queue.json()["items"][0]["inbound_order_id"] == inbound_id  # assert queue.json()['ite
    item_id = queue.json()["items"][0]["items"][0]["inbound_item_id"]  # item_id = queue.json()['

    confirmed = client.post(  # confirmed = client.post(
        f"/api/v1/receivings/{inbound_id}/confirm",  # f'/api/v1/receivings/{in
        headers=_headers(client, "operator", "in-receive"),  # headers=_headers(client,
        json={"note": "少收一件", "items": [{"inbound_item_id": item_id, "received_quantity": 4}]},  # json={'note': '少收一件', 'i
    )  # )
    assert confirmed.status_code == 200  # assert confirmed.status_
    assert confirmed.json()["status"] == "confirmed"  # assert confirmed.json()[
    availability = client.get("/api/v1/inventory/1/availability", headers=_headers(client, "operator"))  # availability = client.ge
    assert availability.json()["quantity"] == 8  # assert availability.json
    empty = client.get("/api/v1/receivings", headers=_headers(client, "operator"))  # empty = client.get('/api
    assert empty.json()["total"] == 0  # assert empty.json()['tot


def test_dashboard_summary_and_charts_include_operational_metrics(client: TestClient):  # def test_dashboard_summa
    summary = client.get("/api/v1/dashboard/summary", headers=_headers(client))  # summary = client.get('/a
    assert summary.status_code == 200  # assert summary.status_co
    body = summary.json()  # body = summary.json()
    assert "pending_approvals" in body  # assert 'pending_approval
    assert "low_stock_alerts" in body  # assert 'low_stock_alerts
    assert "pending_receiving" in body  # assert 'pending_receivin
    assert "pending_review" in body  # assert 'pending_review' 
    charts = client.get("/api/v1/dashboard/charts", headers=_headers(client))  # charts = client.get('/ap
    assert charts.status_code == 200  # assert charts.status_cod
    payload = charts.json()  # payload = charts.json()
    assert "inbound_by_day" in payload  # assert 'inbound_by_day' 
    assert "outbound_by_day" in payload  # assert 'outbound_by_day'
    assert "stock_by_warehouse" in payload  # assert 'stock_by_warehou
    assert payload["stock_by_warehouse"][0]["quantity"] == 4  # assert payload['stock_by


def test_admin_can_manage_users_and_catalog(client: TestClient):  # def test_admin_can_manag
    created_user = client.post(  # created_user = client.po
        "/api/v1/users",  # '/api/v1/users',
        headers=_headers(client, key="user-create"),  # headers=_headers(client,
        json={  # json={
            "username": "clerk",  # 'username': 'clerk',
            "password": "password",  # 'password': 'password',
            "display_name": "仓管员",  # 'display_name': '仓管员',
            "roles": ["warehouse_operator"],  # 'roles': ['warehouse_ope
            "warehouse_ids": [1],  # 'warehouse_ids': [1],
        },  # },
    )  # )
    assert created_user.status_code == 201  # assert created_user.stat
    user_id = created_user.json()["user_id"]  # user_id = created_user.j
    listed = client.get("/api/v1/users", headers=_headers(client))  # listed = client.get('/ap
    assert listed.status_code == 200  # assert listed.status_cod
    assert any(item["username"] == "clerk" for item in listed.json()["items"])  # assert any(item['usernam
    updated = client.patch(  # updated = client.patch(
        f"/api/v1/users/{user_id}",  # f'/api/v1/users/{user_id
        headers=_headers(client, key="user-update"),  # headers=_headers(client,
        json={"is_active": False, "roles": ["viewer"], "warehouse_ids": []},  # json={'is_active': False
    )  # )
    assert updated.status_code == 200  # assert updated.status_co
    assert updated.json()["is_active"] is False  # assert updated.json()['i
    assert updated.json()["roles"] == ["viewer"]  # assert updated.json()['r

    forbidden = client.post(  # forbidden = client.post(
        "/api/v1/users",  # '/api/v1/users',
        headers=_headers(client, "operator", "user-forbidden"),  # headers=_headers(client,
        json={"username": "nope", "password": "password", "display_name": "x", "roles": ["viewer"]},  # json={'username': 'nope'
    )  # )
    assert forbidden.status_code == 403  # assert forbidden.status_

    aliased = client.post(  # aliased = client.post(
        "/api/v1/users",  # '/api/v1/users',
        headers=_headers(client, key="user-alias"),  # headers=_headers(client,
        json={  # json={
            "username": "alias-op",  # 'username': 'alias-op',
            "password": "password",  # 'password': 'password',
            "display_name": "别名操作员",  # 'display_name': '别名操作员',
            "roles": ["operator"],  # 'roles': ['operator'],
            "warehouse_ids": [1],  # 'warehouse_ids': [1],
        },  # },
    )  # )
    assert aliased.status_code == 201  # assert aliased.status_co
    assert "warehouse_operator" in aliased.json()["roles"] or "operator" in aliased.json()["roles"]  # assert 'warehouse_operat

    product = client.post(  # product = client.post(
        "/api/v1/products",  # '/api/v1/products',
        headers=_headers(client, key="product-create"),  # headers=_headers(client,
        json={  # json={
            "sku_code": "SKU-NEW",  # 'sku_code': 'SKU-NEW',
            "source_product_code": "SRC-NEW",  # 'source_product_code': '
            "brand": "品牌",  # 'brand': '品牌',
            "product_name": "新商品",  # 'product_name': '新商品',
            "category": "分类",  # 'category': '分类',
            "size": "标准",  # 'size': '标准',
            "function_feature": "普通",  # 'function_feature': '普通'
            "color": "红",  # 'color': '红',
            "pallet_spec": "箱",  # 'pallet_spec': '箱',
            "pallet_capacity": 8,  # 'pallet_capacity': 8,
        },  # },
    )  # )
    assert product.status_code == 201  # assert product.status_co
    location = client.post(  # location = client.post(
        "/api/v1/locations",  # '/api/v1/locations',
        headers=_headers(client, key="location-create"),  # headers=_headers(client,
        json={  # json={
            "warehouse_id": 1,  # 'warehouse_id': 1,
            "location_code": "B-01",  # 'location_code': 'B-01',
            "zone_code": "B",  # 'zone_code': 'B',
            "aisle_code": "01",  # 'aisle_code': '01',
            "rack_code": "01",  # 'rack_code': '01',
            "position_code": "01",  # 'position_code': '01',
        },  # },
    )  # )
    assert location.status_code == 201  # assert location.status_c

    warehouse = client.post(  # warehouse = client.post(
        "/api/v1/warehouses",  # '/api/v1/warehouses',
        headers=_headers(client, key="warehouse-create"),  # headers=_headers(client,
        json={"warehouse_code": "WH-NEW", "warehouse_name": "新建仓"},  # json={'warehouse_code': 
    )  # )
    assert warehouse.status_code == 201  # assert warehouse.status_
    assert warehouse.json()["warehouse_code"] == "WH-NEW"  # assert warehouse.json()[

    deleted = client.delete(  # deleted = client.delete(
        f"/api/v1/users/{user_id}",  # f'/api/v1/users/{user_id
        headers=_headers(client, key="user-delete"),  # headers=_headers(client,
    )  # )
    assert deleted.status_code == 200  # assert deleted.status_co
    assert deleted.json()["deleted"] is True  # assert deleted.json()['d
    listed_after = client.get("/api/v1/users", headers=_headers(client))  # listed_after = client.ge
    assert all(item["username"] != "clerk" or item["is_active"] is False for item in listed_after.json()["items"])  # assert all(item['usernam
    self_delete = client.delete("/api/v1/users/1", headers=_headers(client, key="user-self-delete"))  # self_delete = client.del
    assert self_delete.status_code == 409  # assert self_delete.statu

    csv_body = (  # csv_body = (
        "sku_code,source_product_code,brand,product_name,category,size,function_feature,color,pallet_spec,pallet_capacity\n"  # 'sku_code,source_product
        "SKU-CSV,SRC-CSV,品牌,CSV商品,分类,标准,普通,蓝,箱,12\n"  # 'SKU-CSV,SRC-CSV,品牌,CSV商
    )  # )
    uploaded = client.post(  # uploaded = client.post(
        "/api/v1/imports",  # '/api/v1/imports',
        headers=_headers(client, key="import-csv"),  # headers=_headers(client,
        json={"filename": "products.csv", "content": csv_body},  # json={'filename': 'produ
    )  # )
    assert uploaded.status_code == 201  # assert uploaded.status_c
    assert uploaded.json()["valid_rows"] == 1  # assert uploaded.json()['
    products = client.get("/api/v1/products?keyword=SKU-CSV", headers=_headers(client))  # products = client.get('/
    assert any(item["sku_code"] == "SKU-CSV" for item in products.json()["items"])  # assert any(item['sku_cod


def test_assistant_queries_inventory_without_changing_stock(client: TestClient):  # def test_assistant_queri
    before = client.get("/api/v1/inventory/1/availability", headers=_headers(client)).json()["quantity"]  # before = client.get('/ap
    created = client.post("/api/v1/agents/sessions", headers=_headers(client, key="agent-session"))  # created = client.post('/
    assert created.status_code == 201  # assert created.status_co
    session_id = created.json()["session_id"]  # session_id = created.jso
    reply = client.post(  # reply = client.post(
        f"/api/v1/agents/sessions/{session_id}/messages",  # f'/api/v1/agents/session
        headers=_headers(client, key="agent-msg"),  # headers=_headers(client,
        json={"content": "查询 SKU-1 的可用库存"},  # json={'content': '查询 SKU
    )  # )
    assert reply.status_code == 200  # assert reply.status_code
    body = reply.json()  # body = reply.json()
    assert body["role"] == "assistant"  # assert body['role'] == '
    assert "SKU-1" in body["content"]  # assert 'SKU-1' in body['
    assert body["tool_calls"]  # assert body['tool_calls'
    assert all(call["name"] != "execute_sql" for call in body["tool_calls"])  # assert all(call['name'] 
    after = client.get("/api/v1/inventory/1/availability", headers=_headers(client)).json()["quantity"]  # after = client.get('/api
    assert after == before  # assert after == before
    draft = client.post(  # draft = client.post(
        f"/api/v1/agents/sessions/{session_id}/messages",  # f'/api/v1/agents/session
        headers=_headers(client, key="agent-draft"),  # headers=_headers(client,
        json={"content": "生成入库单草稿 SKU-1 库位 A-01 数量 2"},  # json={'content': '生成入库单草
    )  # )
    assert draft.status_code == 200  # assert draft.status_code
    assert draft.json()["draft"]["type"] == "inbound"  # assert draft.json()['dra
    assert client.get("/api/v1/inbounds", headers=_headers(client)).json()["items"] == []  # assert client.get('/api/


def test_assistant_followup_reuses_sku_from_history(client: TestClient):  # def test_assistant_follo
    created = client.post("/api/v1/agents/sessions", headers=_headers(client, key="agent-history-session"))  # created = client.post('/
    session_id = created.json()["session_id"]  # session_id = created.jso
    first = client.post(  # first = client.post(
        f"/api/v1/agents/sessions/{session_id}/messages",  # f'/api/v1/agents/session
        headers=_headers(client, key="agent-history-first"),  # headers=_headers(client,
        json={"content": "查询 SKU-1 的可用库存"},  # json={'content': '查询 SKU
    )  # )
    assert first.status_code == 200  # assert first.status_code
    assert "SKU-1" in first.json()["content"]  # assert 'SKU-1' in first.
    follow = client.post(  # follow = client.post(
        f"/api/v1/agents/sessions/{session_id}/messages",  # f'/api/v1/agents/session
        headers=_headers(client, key="agent-history-follow"),  # headers=_headers(client,
        json={"content": "这个还有多少"},  # json={'content': '这个还有多少
    )  # )
    assert follow.status_code == 200  # assert follow.status_cod
    body = follow.json()  # body = follow.json()
    assert "SKU-1" in body["content"]  # assert 'SKU-1' in body['
    assert "请提供系统 SKU" not in body["content"]  # assert '请提供系统 SKU' not i
    assert any(call["name"] == "query_inventory" for call in body["tool_calls"])  # assert any(call['name'] 
    assert body["draft"] is None  # assert body['draft'] is 


def test_assistant_suggests_next_step_when_stock_is_low(client: TestClient):  # def test_assistant_sugge
    created = client.post("/api/v1/agents/sessions", headers=_headers(client, key="agent-suggest-session"))  # created = client.post('/
    session_id = created.json()["session_id"]  # session_id = created.jso
    reply = client.post(  # reply = client.post(
        f"/api/v1/agents/sessions/{session_id}/messages",  # f'/api/v1/agents/session
        headers=_headers(client, key="agent-suggest"),  # headers=_headers(client,
        json={"content": "查询 SKU-1 的可用库存"},  # json={'content': '查询 SKU
    )  # )
    assert reply.status_code == 200  # assert reply.status_code
    content = reply.json()["content"]  # content = reply.json()['
    assert "SKU-1" in content  # assert 'SKU-1' in conten
    assert "建议" in content  # assert '建议' in content
    assert "预警" in content or "入库" in content  # assert '预警' in content o


def test_assistant_hello_does_not_dump_inventory(client: TestClient):  # def test_assistant_hello
    created = client.post("/api/v1/agents/sessions", headers=_headers(client, key="agent-hello-session"))  # created = client.post('/
    session_id = created.json()["session_id"]  # session_id = created.jso
    reply = client.post(  # reply = client.post(
        f"/api/v1/agents/sessions/{session_id}/messages",  # f'/api/v1/agents/session
        headers=_headers(client, key="agent-hello"),  # headers=_headers(client,
        json={"content": "你好"},  # json={'content': '你好'},
    )  # )
    assert reply.status_code == 200  # assert reply.status_code
    body = reply.json()  # body = reply.json()
    assert "仓储助手" in body["content"]  # assert '仓储助手' in body['c
    assert "未对库存做任何变更" not in body["content"]  # assert '未对库存做任何变更' not i
    assert "| SKU |" not in body["content"]  # assert '| SKU |' not in 
    assert "MS-" not in body["content"]  # assert 'MS-' not in body
    assert body["tool_calls"] == []  # assert body['tool_calls'
    assert body["draft"] is None  # assert body['draft'] is 


def test_assistant_clear_session_wipes_messages_without_creating_another_session(client: TestClient):  # def test_assistant_clear
    created = client.post("/api/v1/agents/sessions", headers=_headers(client, key="agent-session-clear"))  # created = client.post('/
    session_id = created.json()["session_id"]  # session_id = created.jso
    client.post(  # client.post(
        f"/api/v1/agents/sessions/{session_id}/messages",  # f'/api/v1/agents/session
        headers=_headers(client, key="agent-msg-before-clear"),  # headers=_headers(client,
        json={"content": "查询 SKU-1 的可用库存"},  # json={'content': '查询 SKU
    )  # )
    listed = client.get("/api/v1/agents/sessions", headers=_headers(client)).json()["items"]  # listed = client.get('/ap
    assert len(listed) == 1  # assert len(listed) == 1
    assert listed[0]["title"] != "新会话"  # assert listed[0]['title'

    cleared = client.post(  # cleared = client.post(
        f"/api/v1/agents/sessions/{session_id}/clear",  # f'/api/v1/agents/session
        headers=_headers(client, key="agent-clear"),  # headers=_headers(client,
    )  # )
    assert cleared.status_code == 200  # assert cleared.status_co
    assert cleared.json()["session_id"] == session_id  # assert cleared.json()['s
    assert cleared.json()["title"] == "新会话"  # assert cleared.json()['t
    messages = client.get(  # messages = client.get(
        f"/api/v1/agents/sessions/{session_id}/messages",  # f'/api/v1/agents/session
        headers=_headers(client),  # headers=_headers(client)
    ).json()["items"]  # ).json()['items']
    assert messages == []  # assert messages == []
    after = client.get("/api/v1/agents/sessions", headers=_headers(client)).json()["items"]  # after = client.get('/api
    assert [item["session_id"] for item in after] == [session_id]  # assert [item['session_id
    assert after[0]["title"] == "新会话"  # assert after[0]['title']


def test_assistant_delete_session_removes_session_and_messages(client: TestClient):  # def test_assistant_delet
    created = client.post("/api/v1/agents/sessions", headers=_headers(client, key="agent-session-delete"))  # created = client.post('/
    session_id = created.json()["session_id"]  # session_id = created.jso
    client.post(  # client.post(
        f"/api/v1/agents/sessions/{session_id}/messages",  # f'/api/v1/agents/session
        headers=_headers(client, key="agent-msg-before-delete"),  # headers=_headers(client,
        json={"content": "查询 SKU-1 的可用库存"},  # json={'content': '查询 SKU
    )  # )
    deleted = client.delete(  # deleted = client.delete(
        f"/api/v1/agents/sessions/{session_id}",  # f'/api/v1/agents/session
        headers=_headers(client, key="agent-delete"),  # headers=_headers(client,
    )  # )
    assert deleted.status_code == 200  # assert deleted.status_co
    assert deleted.json() == {"session_id": session_id, "deleted": True}  # assert deleted.json() ==
    listed = client.get("/api/v1/agents/sessions", headers=_headers(client)).json()["items"]  # listed = client.get('/ap
    assert listed == []  # assert listed == []
    missing = client.get(f"/api/v1/agents/sessions/{session_id}/messages", headers=_headers(client))  # missing = client.get(f'/
    assert missing.status_code == 404  # assert missing.status_co
    replay = client.delete(  # replay = client.delete(
        f"/api/v1/agents/sessions/{session_id}",  # f'/api/v1/agents/session
        headers=_headers(client, key="agent-delete"),  # headers=_headers(client,
    )  # )
    assert replay.status_code == 200  # assert replay.status_cod
    assert replay.json()["deleted"] is True  # assert replay.json()['de
    again = client.delete(  # again = client.delete(
        f"/api/v1/agents/sessions/{session_id}",  # f'/api/v1/agents/session
        headers=_headers(client, key="agent-delete-again"),  # headers=_headers(client,
    )  # )
    assert again.status_code == 200  # assert again.status_code
    assert again.json() == {"session_id": session_id, "deleted": True}  # assert again.json() == {


def test_assistant_sessions_and_messages_are_isolated_per_user(client: TestClient, caplog):  # def test_assistant_sessi
    import logging  # import logging

    caplog.set_level(logging.INFO, logger="erp.agent")  # caplog.set_level(logging
    admin = _headers(client, key="agent-admin-session")  # admin = _headers(client,
    admin_session = client.post("/api/v1/agents/sessions", headers=admin)  # admin_session = client.p
    admin_id = admin_session.json()["session_id"]  # admin_id = admin_session
    admin_me = client.get("/api/v1/auth/me", headers=_headers(client)).json()["user_id"]  # admin_me = client.get('/
    client.post(  # client.post(
        f"/api/v1/agents/sessions/{admin_id}/messages",  # f'/api/v1/agents/session
        headers=_headers(client, key="agent-admin-msg"),  # headers=_headers(client,
        json={"content": "查询 SKU-1 的可用库存"},  # json={'content': '查询 SKU
    )  # )
    assert f"user_id={admin_me}" in caplog.text  # assert f'user_id={admin_
    assert f"session_id={admin_id}" in caplog.text  # assert f'session_id={adm

    operator = _headers(client, "operator", key="agent-op-session")  # operator = _headers(clie
    listed = client.get("/api/v1/agents/sessions", headers=operator)  # listed = client.get('/ap
    assert listed.json()["items"] == []  # assert listed.json()['it
    hidden = client.get(f"/api/v1/agents/sessions/{admin_id}/messages", headers=operator)  # hidden = client.get(f'/a
    assert hidden.status_code == 404  # assert hidden.status_cod
    stolen = client.post(  # stolen = client.post(
        f"/api/v1/agents/sessions/{admin_id}/messages",  # f'/api/v1/agents/session
        headers=_headers(client, "operator", key="agent-op-steal"),  # headers=_headers(client,
        json={"content": "查看预警"},  # json={'content': '查看预警'}
    )  # )
    assert stolen.status_code == 404  # assert stolen.status_cod
    assert "session denied" in caplog.text  # assert 'session denied' 

    second = client.post("/api/v1/agents/sessions", headers=_headers(client, key="agent-admin-session-2"))  # second = client.post('/a
    second_id = second.json()["session_id"]  # second_id = second.json(
    client.post(  # client.post(
        f"/api/v1/agents/sessions/{second_id}/messages",  # f'/api/v1/agents/session
        headers=_headers(client, key="agent-admin-msg-2"),  # headers=_headers(client,
        json={"content": "查看预警"},  # json={'content': '查看预警'}
    )  # )
    first_messages = client.get(  # first_messages = client.
        f"/api/v1/agents/sessions/{admin_id}/messages",  # f'/api/v1/agents/session
        headers=_headers(client),  # headers=_headers(client)
    ).json()["items"]  # ).json()['items']
    second_messages = client.get(  # second_messages = client
        f"/api/v1/agents/sessions/{second_id}/messages",  # f'/api/v1/agents/session
        headers=_headers(client),  # headers=_headers(client)
    ).json()["items"]  # ).json()['items']
    assert any("SKU-1" in item["content"] for item in first_messages)  # assert any('SKU-1' in it
    assert all("查看预警" not in (item["content"] or "") for item in first_messages)  # assert all('查看预警' not in
    assert any("预警" in item["content"] for item in second_messages)  # assert any('预警' in item[
    assert all("SKU-1" not in (item["content"] or "") for item in second_messages)  # assert all('SKU-1' not i


def test_export_inventory_csv_and_acknowledge_alert(client: TestClient):  # def test_export_inventor
    export = client.get("/api/v1/exports/inventory", headers=_headers(client))  # export = client.get('/ap
    assert export.status_code == 200  # assert export.status_cod
    assert "text/csv" in export.headers["content-type"]  # assert 'text/csv' in exp
    assert "SKU-1" in export.text  # assert 'SKU-1' in export
    alerts = client.get("/api/v1/alerts", headers=_headers(client))  # alerts = client.get('/ap
    assert alerts.status_code == 200  # assert alerts.status_cod
    balance_id = alerts.json()["items"][0]["balance_id"]  # balance_id = alerts.json
    acked = client.post(  # acked = client.post(
        f"/api/v1/alerts/{balance_id}/ack",  # f'/api/v1/alerts/{balanc
        headers=_headers(client, key="alert-ack"),  # headers=_headers(client,
        json={"note": "已安排补货"},  # json={'note': '已安排补货'},
    )  # )
    assert acked.status_code == 200  # assert acked.status_code
    assert acked.json()["status"] == "acked"  # assert acked.json()['sta
    refreshed = client.get("/api/v1/alerts", headers=_headers(client))  # refreshed = client.get('
    assert refreshed.json()["items"][0]["status"] == "acked"  # assert refreshed.json()[


def test_extension_tables_include_followup_entities():  # def test_extension_table
    from backend.app.db.base import Base as MetadataBase  # from backend.app.db.base

    assert {"alert_ack", "agent_session", "agent_message"}.issubset(MetadataBase.metadata.tables)  # assert {'alert_ack', 'ag
