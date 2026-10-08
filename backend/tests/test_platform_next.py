"""用户、导入、报表等后续接口。"""

from pathlib import Path  # from pathlib import Path

from fastapi.testclient import TestClient  # from fastapi.testclient 

from backend.tests.test_followup_api import _headers  # from backend.tests.test_

pytest_plugins = ["backend.tests.test_followup_api"]  # pytest_plugins = ['backe

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # PROJECT_ROOT = Path(__fi


def test_dashboard_cache_invalidates_after_inbound(client: TestClient):  # def test_dashboard_cache
    headers = _headers(client)  # headers = _headers(clien
    before = client.get("/api/v1/dashboard/summary", headers=headers).json()["stock_quantity"]  # before = client.get('/ap
    created = client.post(  # created = client.post(
        "/api/v1/inbounds",  # '/api/v1/inbounds',
        headers=_headers(client, key="cache-in"),  # headers=_headers(client,
        json={"order_no": "IN-CACHE", "items": [{"product_id": 1, "location_id": 1, "quantity": 5}]},  # json={'order_no': 'IN-CA
    )  # )
    inbound_id = created.json()["inbound_order_id"]  # inbound_id = created.jso
    assert (  # assert (
        client.post(  # client.post(
            f"/api/v1/inbounds/{inbound_id}/confirm",  # f'/api/v1/inbounds/{inbo
            headers=_headers(client, key="cache-confirm"),  # headers=_headers(client,
        ).status_code  # ).status_code
        == 200  # == 200
    )  # )
    after = client.get("/api/v1/dashboard/summary", headers=headers).json()["stock_quantity"]  # after = client.get('/api
    assert after == before + 5  # assert after == before +


def test_reports_classify_abc_and_turnover(client: TestClient):  # def test_reports_classif
    headers = _headers(client)  # headers = _headers(clien
    abc = client.get("/api/v1/reports/abc", headers=headers)  # abc = client.get('/api/v
    assert abc.status_code == 200  # assert abc.status_code =
    items = abc.json()["items"]  # items = abc.json()['item
    assert items  # assert items
    assert items[0]["class"] in {"A", "B", "C"}  # assert items[0]['class']
    assert items[0]["sku_code"] == "SKU-1"  # assert items[0]['sku_cod
    assert abs(sum(item["share"] for item in items) - 1) < 1e-6  # assert abs(sum(item['sha

    turnover = client.get("/api/v1/reports/turnover", headers=headers)  # turnover = client.get('/
    assert turnover.status_code == 200  # assert turnover.status_c
    row = turnover.json()["items"][0]  # row = turnover.json()['i
    assert row["sku_code"] == "SKU-1"  # assert row['sku_code'] =
    assert "turnover_rate" in row  # assert 'turnover_rate' i
    assert "outbound_quantity" in row  # assert 'outbound_quantit


def test_langgraph_agents_use_whitelist_tools_only(client: TestClient):  # def test_langgraph_agent
    from backend.app.agents.tools import FORBIDDEN_TOOLS, WHITELIST_TOOLS  # from backend.app.agents.

    assert "query_inventory" in WHITELIST_TOOLS  # assert 'query_inventory'
    assert "execute_raw_sql" in FORBIDDEN_TOOLS  # assert 'execute_raw_sql'
    assert not (WHITELIST_TOOLS & FORBIDDEN_TOOLS)  # assert not (WHITELIST_TO

    session = client.post("/api/v1/agents/sessions", headers=_headers(client, key="lg-session"))  # session = client.post('/
    reply = client.post(  # reply = client.post(
        f"/api/v1/agents/sessions/{session.json()['session_id']}/messages",  # f'/api/v1/agents/session
        headers=_headers(client, key="lg-msg"),  # headers=_headers(client,
        json={"content": "查询 SKU-1 的可用库存"},  # json={'content': '查询 SKU
    )  # )
    assert reply.status_code == 200  # assert reply.status_code
    body = reply.json()  # body = reply.json()
    assert body["tool_calls"]  # assert body['tool_calls'
    assert all(call["name"] in WHITELIST_TOOLS for call in body["tool_calls"])  # assert all(call['name'] 
    assert all(call.get("agent") for call in body["tool_calls"])  # assert all(call.get('age
    assert "execute_sql" not in {call["name"] for call in body["tool_calls"]}  # assert 'execute_sql' not


def test_system_runtime_exposes_cache_and_graph(client: TestClient):  # def test_system_runtime_
    runtime = client.get("/api/v1/system/runtime", headers=_headers(client))  # runtime = client.get('/a
    assert runtime.status_code == 200  # assert runtime.status_co
    body = runtime.json()  # body = runtime.json()
    assert body["cache_backend"] in {"memory", "redis"}  # assert body['cache_backe
    assert body["graph_engine"] == "langgraph"  # assert body['graph_engin
    assert body["llm_provider"] in {"none", "deepseek"}  # assert body['llm_provide
    assert body["inventory_source"] == "mysql"  # assert body['inventory_s


def test_assistant_routes_abc_questions_to_report_tool(client: TestClient):  # def test_assistant_route
    session = client.post("/api/v1/agents/sessions", headers=_headers(client, key="abc-session"))  # session = client.post('/
    reply = client.post(  # reply = client.post(
        f"/api/v1/agents/sessions/{session.json()['session_id']}/messages",  # f'/api/v1/agents/session
        headers=_headers(client, key="abc-msg"),  # headers=_headers(client,
        json={"content": "请给出 SKU 的 ABC 分类"},  # json={'content': '请给出 SK
    )  # )
    assert reply.status_code == 200  # assert reply.status_code
    names = {call["name"] for call in reply.json()["tool_calls"]}  # names = {call['name'] fo
    assert "query_abc_report" in names  # assert 'query_abc_report
    assert reply.json()["tool_calls"][0]["agent"] == "analysis_agent"  # assert reply.json()['too


def test_assistant_format_table_tool_renders_markdown(client: TestClient):  # def test_assistant_forma
    from backend.app.agents.tools import WHITELIST_TOOLS  # from backend.app.agents.
    from backend.app.services.assistant_service import format_markdown_table  # from backend.app.service

    assert "format_table" in WHITELIST_TOOLS  # assert 'format_table' in
    markdown = format_markdown_table(  # markdown = format_markdo
        ["SKU", "分类"],  # ['SKU', '分类'],
        [{"SKU": "SKU-1", "分类": "A"}, {"SKU": "SKU-2", "分类": "B"}],  # [{'SKU': 'SKU-1', '分类': 
    )  # )
    assert markdown.splitlines()[0] == "| SKU | 分类 |"  # assert markdown.splitlin
    assert "| SKU-1 | A |" in markdown  # assert '| SKU-1 | A |' i

    session = client.post("/api/v1/agents/sessions", headers=_headers(client, key="table-session"))  # session = client.post('/
    reply = client.post(  # reply = client.post(
        f"/api/v1/agents/sessions/{session.json()['session_id']}/messages",  # f'/api/v1/agents/session
        headers=_headers(client, key="table-msg"),  # headers=_headers(client,
        json={"content": "把 SKU 的 ABC 分类制成表格"},  # json={'content': '把 SKU 
    )  # )
    assert reply.status_code == 200  # assert reply.status_code
    names = {call["name"] for call in reply.json()["tool_calls"]}  # names = {call['name'] fo
    assert "query_abc_report" in names  # assert 'query_abc_report
    assert "format_table" in names  # assert 'format_table' in
    content = reply.json()["content"]  # content = reply.json()['
    assert "|" in content  # assert '|' in content
    assert "SKU" in content or "sku" in content.lower()  # assert 'SKU' in content 


def test_docker_compose_wires_mysql_redis_and_apps():  # def test_docker_compose_
    compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")  # compose = (PROJECT_ROOT 
    assert "mysql:" in compose  # assert 'mysql:' in compo
    assert "redis:" in compose  # assert 'redis:' in compo
    assert "backend:" in compose  # assert 'backend:' in com
    assert "frontend:" in compose  # assert 'frontend:' in co
    assert "REDIS_URL" in compose  # assert 'REDIS_URL' in co
    assert "DROP TABLE" not in compose.upper()  # assert 'DROP TABLE' not 


def _confirm_inbound(client: TestClient, order_no: str, product_id: int, quantity: int, key: str) -> None:  # def _confirm_inbound(cli
    created = client.post(  # created = client.post(
        "/api/v1/inbounds",  # '/api/v1/inbounds',
        headers=_headers(client, key=f"{key}-create"),  # headers=_headers(client,
        json={"order_no": order_no, "items": [{"product_id": product_id, "location_id": 1, "quantity": quantity}]},  # json={'order_no': order_
    )  # )
    inbound_id = created.json()["inbound_order_id"]  # inbound_id = created.jso
    assert (  # assert (
        client.post(  # client.post(
            f"/api/v1/inbounds/{inbound_id}/confirm",  # f'/api/v1/inbounds/{inbo
            headers=_headers(client, key=f"{key}-confirm"),  # headers=_headers(client,
        ).status_code  # ).status_code
        == 200  # == 200
    )  # )


def test_daily_weekly_and_picking_efficiency_reports(client: TestClient):  # def test_daily_weekly_an
    headers = _headers(client)  # headers = _headers(clien
    _confirm_inbound(client, "IN-DAILY", 1, 5, "daily")  # _confirm_inbound(client,
    daily = client.get("/api/v1/reports/daily", headers=headers)  # daily = client.get('/api
    assert daily.status_code == 200  # assert daily.status_code
    days = daily.json()["items"]  # days = daily.json()['ite
    assert len(days) == 7  # assert len(days) == 7
    assert days[-1]["inbound_quantity"] == 5  # assert days[-1]['inbound
    assert "outbound_quantity" in days[-1]  # assert 'outbound_quantit
    assert "date" in days[-1]  # assert 'date' in days[-1

    weekly = client.get("/api/v1/reports/weekly", headers=headers)  # weekly = client.get('/ap
    assert weekly.status_code == 200  # assert weekly.status_cod
    weeks = weekly.json()["items"]  # weeks = weekly.json()['i
    assert len(weeks) == 4  # assert len(weeks) == 4
    assert weeks[-1]["inbound_quantity"] == 5  # assert weeks[-1]['inboun
    assert "week" in weeks[-1]  # assert 'week' in weeks[-

    picking = client.get("/api/v1/reports/picking-efficiency", headers=headers)  # picking = client.get('/a
    assert picking.status_code == 200  # assert picking.status_co
    body = picking.json()  # body = picking.json()
    assert body["total_tasks"] == 0  # assert body['total_tasks
    assert body["completed_tasks"] == 0  # assert body['completed_t
    assert body["completion_rate"] == 0  # assert body['completion_

    daily_range = client.get("/api/v1/reports/daily?days=14", headers=headers)  # daily_range = client.get
    assert daily_range.status_code == 200  # assert daily_range.statu
    assert daily_range.json()["days"] == 14  # assert daily_range.json(
    assert len(daily_range.json()["items"]) == 14  # assert len(daily_range.j


def test_abc_skips_zero_score_products(client: TestClient):  # def test_abc_skips_zero_
    client.post(  # client.post(
        "/api/v1/products",  # '/api/v1/products',
        headers=_headers(client, key="abc-zero-product"),  # headers=_headers(client,
        json={  # json={
            "sku_code": "SKU-ZERO",  # 'sku_code': 'SKU-ZERO',
            "source_product_code": "SRC-ZERO",  # 'source_product_code': '
            "brand": "品牌",  # 'brand': '品牌',
            "product_name": "零分商品",  # 'product_name': '零分商品',
            "category": "分类",  # 'category': '分类',
            "size": "标准",  # 'size': '标准',
            "function_feature": "普通",  # 'function_feature': '普通'
            "color": "白",  # 'color': '白',
            "pallet_spec": "箱",  # 'pallet_spec': '箱',
            "pallet_capacity": 10,  # 'pallet_capacity': 10,
        },  # },
    )  # )
    items = client.get("/api/v1/reports/abc", headers=_headers(client)).json()["items"]  # items = client.get('/api
    assert all(item["sku_code"] != "SKU-ZERO" for item in items)  # assert all(item['sku_cod
    assert all(item["score"] > 0 for item in items)  # assert all(item['score']
    assert abs(sum(item["share"] for item in items) - 1) < 1e-6  # assert abs(sum(item['sha


def test_picking_elapsed_seconds_normalizes_timezones():  # def test_picking_elapsed
    from datetime import UTC, datetime, timedelta, timezone  # from datetime import UTC

    from backend.app.services.report_service import elapsed_seconds  # from backend.app.service

    created = datetime(2026, 9, 15, 10, 0, 0)  # created = datetime(2026,
    confirmed = datetime(2026, 9, 15, 10, 5, 0, tzinfo=UTC)  # confirmed = datetime(202
    assert elapsed_seconds(created, confirmed) == 300  # assert elapsed_seconds(c
    created_cn = datetime(2026, 9, 15, 18, 0, 0, tzinfo=timezone(timedelta(hours=8)))  # created_cn = datetime(20
    confirmed_naive = datetime(2026, 9, 15, 10, 5, 0)  # confirmed_naive = dateti
    assert elapsed_seconds(created_cn, confirmed_naive) == 300  # assert elapsed_seconds(c


def test_availability_cache_invalidates_after_inbound(client: TestClient):  # def test_availability_ca
    headers = _headers(client)  # headers = _headers(clien
    before = client.get("/api/v1/inventory/1/availability", headers=headers).json()["quantity"]  # before = client.get('/ap
    _confirm_inbound(client, "IN-AVAIL", 1, 3, "avail")  # _confirm_inbound(client,
    after = client.get("/api/v1/inventory/1/availability", headers=headers).json()["quantity"]  # after = client.get('/api
    assert after == before + 3  # assert after == before +


def test_alerts_include_stale_stock_for_high_on_hand(client: TestClient):  # def test_alerts_include_
    product = client.post(  # product = client.post(
        "/api/v1/products",  # '/api/v1/products',
        headers=_headers(client, key="stale-product"),  # headers=_headers(client,
        json={  # json={
            "sku_code": "SKU-STALE",  # 'sku_code': 'SKU-STALE',
            "source_product_code": "SRC-STALE",  # 'source_product_code': '
            "brand": "品牌",  # 'brand': '品牌',
            "product_name": "呆滞商品",  # 'product_name': '呆滞商品',
            "category": "分类",  # 'category': '分类',
            "size": "标准",  # 'size': '标准',
            "function_feature": "普通",  # 'function_feature': '普通'
            "color": "灰",  # 'color': '灰',
            "pallet_spec": "箱",  # 'pallet_spec': '箱',
            "pallet_capacity": 10,  # 'pallet_capacity': 10,
        },  # },
    )  # )
    assert product.status_code == 201  # assert product.status_co
    product_id = product.json()["product_id"]  # product_id = product.jso
    _confirm_inbound(client, "IN-STALE", product_id, 40, "stale-in")  # _confirm_inbound(client,
    alerts = client.get("/api/v1/alerts", headers=_headers(client))  # alerts = client.get('/ap
    assert alerts.status_code == 200  # assert alerts.status_cod
    stale = [item for item in alerts.json()["items"] if item["alert_type"] == "stale_stock"]  # stale = [item for item i
    assert stale  # assert stale
    assert any(item["sku_code"] == "SKU-STALE" or item["product_id"] == product_id for item in stale)  # assert any(item['sku_cod
    assert all(item["status"] in {"pending", "acked"} for item in stale)  # assert all(item['status'


def test_assistant_answers_daily_and_picking_questions(client: TestClient):  # def test_assistant_answe
    session = client.post("/api/v1/agents/sessions", headers=_headers(client, key="kpi-session"))  # session = client.post('/
    session_id = session.json()["session_id"]  # session_id = session.jso
    daily = client.post(  # daily = client.post(
        f"/api/v1/agents/sessions/{session_id}/messages",  # f'/api/v1/agents/session
        headers=_headers(client, key="kpi-daily"),  # headers=_headers(client,
        json={"content": "查看库存日报"},  # json={'content': '查看库存日报
    )  # )
    assert daily.status_code == 200  # assert daily.status_code
    assert daily.json()["tool_calls"][0]["name"] == "query_daily_report"  # assert daily.json()['too
    picking = client.post(  # picking = client.post(
        f"/api/v1/agents/sessions/{session_id}/messages",  # f'/api/v1/agents/session
        headers=_headers(client, key="kpi-pick"),  # headers=_headers(client,
        json={"content": "拣货效率怎么样"},  # json={'content': '拣货效率怎么
    )  # )
    assert picking.status_code == 200  # assert picking.status_co
    assert picking.json()["tool_calls"][0]["name"] == "query_picking_efficiency"  # assert picking.json()['t
    names = {call["name"] for call in daily.json()["tool_calls"]}  # names = {call['name'] fo
    assert "format_table" in names  # assert 'format_table' in
    assert "|" in daily.json()["content"]  # assert '|' in daily.json


def test_assistant_matches_mega_star_sku_codes(client: TestClient):  # def test_assistant_match
    product = client.post(  # product = client.post(
        "/api/v1/products",  # '/api/v1/products',
        headers=_headers(client, key="ms-product"),  # headers=_headers(client,
        json={  # json={
            "sku_code": "MS-AlOv001",  # 'sku_code': 'MS-AlOv001'
            "source_product_code": "AlOv001",  # 'source_product_code': '
            "brand": "Mega Star",  # 'brand': 'Mega Star',
            "product_name": "铝框",  # 'product_name': '铝框',
            "category": "分类",  # 'category': '分类',
            "size": "标准",  # 'size': '标准',
            "function_feature": "普通",  # 'function_feature': '普通'
            "color": "银",  # 'color': '银',
            "pallet_spec": "箱",  # 'pallet_spec': '箱',
            "pallet_capacity": 10,  # 'pallet_capacity': 10,
        },  # },
    )  # )
    product_id = product.json()["product_id"]  # product_id = product.jso
    _confirm_inbound(client, "IN-MS", product_id, 6, "ms-in")  # _confirm_inbound(client,
    session = client.post("/api/v1/agents/sessions", headers=_headers(client, key="ms-session"))  # session = client.post('/
    reply = client.post(  # reply = client.post(
        f"/api/v1/agents/sessions/{session.json()['session_id']}/messages",  # f'/api/v1/agents/session
        headers=_headers(client, key="ms-msg"),  # headers=_headers(client,
        json={"content": "查询 MS-AlOv001 的可用库存"},  # json={'content': '查询 MS-
    )  # )
    assert reply.status_code == 200  # assert reply.status_code
    assert "MS-AlOv001" in reply.json()["content"]  # assert 'MS-AlOv001' in r
    assert reply.json()["tool_calls"][0]["name"] == "query_inventory"  # assert reply.json()['too
    sku = (reply.json()["tool_calls"][0].get("arguments") or {}).get("sku_code")  # sku = (reply.json()['too
    assert sku in {"MS-AlOv001", "MS-ALOV001"}  # assert sku in {'MS-AlOv0
