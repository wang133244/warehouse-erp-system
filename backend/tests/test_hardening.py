"""冻结量、停用标志。"""

from fastapi.testclient import TestClient  # from fastapi.testclient 

from backend.app.models import Product, StockBalance, WarehouseLocation  # from backend.app.models 
from backend.tests.test_followup_api import _headers  # from backend.tests.test_

pytest_plugins = ["backend.tests.test_followup_api"]  # pytest_plugins = ['backe


def test_admin_can_patch_product_and_location_active_flag(client: TestClient):  # def test_admin_can_patch
    product = client.patch(  # product = client.patch(
        "/api/v1/products/1",  # '/api/v1/products/1',
        headers=_headers(client, key="product-disable"),  # headers=_headers(client,
        json={"is_active": False, "product_name": "停用商品"},  # json={'is_active': False
    )  # )
    assert product.status_code == 200  # assert product.status_co
    assert product.json()["is_active"] is False  # assert product.json()['i
    assert product.json()["product_name"] == "停用商品"  # assert product.json()['p

    inbound = client.post(  # inbound = client.post(
        "/api/v1/inbounds",  # '/api/v1/inbounds',
        headers=_headers(client, "operator", "in-disabled-product"),  # headers=_headers(client,
        json={"order_no": "IN-DISABLED", "items": [{"product_id": 1, "location_id": 1, "quantity": 1}]},  # json={'order_no': 'IN-DI
    )  # )
    assert inbound.status_code == 409  # assert inbound.status_co
    assert inbound.json()["code"] == "PRODUCT_INACTIVE"  # assert inbound.json()['c

    restored = client.patch(  # restored = client.patch(
        "/api/v1/products/1",  # '/api/v1/products/1',
        headers=_headers(client, key="product-enable"),  # headers=_headers(client,
        json={"is_active": True},  # json={'is_active': True}
    )  # )
    assert restored.status_code == 200  # assert restored.status_c
    assert restored.json()["is_active"] is True  # assert restored.json()['

    location = client.patch(  # location = client.patch(
        "/api/v1/locations/1",  # '/api/v1/locations/1',
        headers=_headers(client, key="location-disable"),  # headers=_headers(client,
        json={"is_active": False},  # json={'is_active': False
    )  # )
    assert location.status_code == 200  # assert location.status_c
    assert location.json()["is_active"] is False  # assert location.json()['

    inbound_location = client.post(  # inbound_location = clien
        "/api/v1/inbounds",  # '/api/v1/inbounds',
        headers=_headers(client, "operator", "in-disabled-location"),  # headers=_headers(client,
        json={"order_no": "IN-LOC-OFF", "items": [{"product_id": 1, "location_id": 1, "quantity": 1}]},  # json={'order_no': 'IN-LO
    )  # )
    assert inbound_location.status_code == 409  # assert inbound_location.
    assert inbound_location.json()["code"] == "LOCATION_INACTIVE"  # assert inbound_location.


def test_operator_cannot_inbound_or_outbound_outside_warehouse_scope(client: TestClient):  # def test_operator_cannot
    forbidden_in = client.post(  # forbidden_in = client.po
        "/api/v1/inbounds",  # '/api/v1/inbounds',
        headers=_headers(client, "operator", "in-wh2"),  # headers=_headers(client,
        json={"order_no": "IN-WH2", "items": [{"product_id": 1, "location_id": 2, "quantity": 1}]},  # json={'order_no': 'IN-WH
    )  # )
    assert forbidden_in.status_code == 403  # assert forbidden_in.stat
    assert forbidden_in.json()["code"] == "WAREHOUSE_SCOPE_FORBIDDEN"  # assert forbidden_in.json

    allowed_in = client.post(  # allowed_in = client.post
        "/api/v1/inbounds",  # '/api/v1/inbounds',
        headers=_headers(client, "operator", "in-wh1"),  # headers=_headers(client,
        json={"order_no": "IN-WH1", "items": [{"product_id": 1, "location_id": 1, "quantity": 1}]},  # json={'order_no': 'IN-WH
    )  # )
    assert allowed_in.status_code == 201  # assert allowed_in.status

    outbound = client.post(  # outbound = client.post(
        "/api/v1/outbounds",  # '/api/v1/outbounds',
        headers=_headers(client, "operator", "out-wh1"),  # headers=_headers(client,
        json={"order_no": "OUT-WH1", "items": [{"product_id": 1, "quantity": 1}]},  # json={'order_no': 'OUT-W
    )  # )
    assert outbound.status_code == 201  # assert outbound.status_c


def test_alerts_support_offset_limit_and_total(client: TestClient):  # def test_alerts_support_
    page = client.get("/api/v1/alerts?offset=0&limit=1", headers=_headers(client))  # page = client.get('/api/
    assert page.status_code == 200  # assert page.status_code 
    body = page.json()  # body = page.json()
    assert body["total"] >= 1  # assert body['total'] >= 
    assert body["offset"] == 0  # assert body['offset'] ==
    assert body["limit"] == 1  # assert body['limit'] == 
    assert len(body["items"]) == 1  # assert len(body['items']
    assert body["items"][0]["alert_type"] == "low_stock"  # assert body['items'][0][


def test_import_batch_detail_is_readable(client: TestClient):  # def test_import_batch_de
    listed = client.get("/api/v1/imports", headers=_headers(client))  # listed = client.get('/ap
    assert listed.status_code == 200  # assert listed.status_cod
    assert listed.json()["total"] >= 1  # assert listed.json()['to
    batch_id = listed.json()["items"][0]["batch_id"]  # batch_id = listed.json()
    detail = client.get(f"/api/v1/imports/{batch_id}", headers=_headers(client))  # detail = client.get(f'/a
    assert detail.status_code == 200  # assert detail.status_cod
    payload = detail.json()  # payload = detail.json()
    assert payload["batch_no"]  # assert payload['batch_no
    assert payload["notes"]  # assert payload['notes']
    assert payload["invalid_rows"] >= 0  # assert payload['invalid_


def test_assistant_lists_session_messages(client: TestClient):  # def test_assistant_lists
    created = client.post("/api/v1/agents/sessions", headers=_headers(client, key="hist-session"))  # created = client.post('/
    session_id = created.json()["session_id"]  # session_id = created.jso
    client.post(  # client.post(
        f"/api/v1/agents/sessions/{session_id}/messages",  # f'/api/v1/agents/session
        headers=_headers(client, key="hist-msg"),  # headers=_headers(client,
        json={"content": "查询 SKU-1 的可用库存"},  # json={'content': '查询 SKU
    )  # )
    history = client.get(  # history = client.get(
        f"/api/v1/agents/sessions/{session_id}/messages",  # f'/api/v1/agents/session
        headers=_headers(client),  # headers=_headers(client)
    )  # )
    assert history.status_code == 200  # assert history.status_co
    items = history.json()["items"]  # items = history.json()['
    assert len(items) >= 2  # assert len(items) >= 2
    assert items[0]["role"] == "user"  # assert items[0]['role'] 
    assert items[-1]["role"] == "assistant"  # assert items[-1]['role']


def test_hardening_columns_exist_on_models():  # def test_hardening_colum
    assert "is_active" in Product.__table__.columns  # assert 'is_active' in Pr
    assert "is_active" in WarehouseLocation.__table__.columns  # assert 'is_active' in Wa
    assert "frozen_quantity" in StockBalance.__table__.columns  # assert 'frozen_quantity'
