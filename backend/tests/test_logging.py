"""request_id 与测试环境不写日志文件。"""

import logging  # import logging

from fastapi import APIRouter  # from fastapi import APIR
from fastapi.testclient import TestClient  # from fastapi.testclient 

from backend.app.core.errors import AppError  # from backend.app.core.er
from backend.app.core.logging import configure_logging, get_logger, set_request_id  # from backend.app.core.lo
from backend.app.main import create_app  # from backend.app.main im


def test_request_id_appears_in_runtime_logs(caplog):  # def test_request_id_appe
    configure_logging(force=True, to_file=False)  # configure_logging(force=
    caplog.set_level(logging.INFO, logger="erp")  # caplog.set_level(logging
    set_request_id("trace-99")  # set_request_id('trace-99
    get_logger("auth").info("login failed username=%s", "alice")  # get_logger('auth').info(
    set_request_id(None)  # set_request_id(None)

    assert "login failed username=alice" in caplog.text  # assert 'login failed use
    assert any(getattr(record, "request_id", None) == "trace-99" for record in caplog.records)  # assert any(getattr(recor


def test_http_access_log_includes_request_id(caplog):  # def test_http_access_log
    configure_logging(force=True, to_file=False)  # configure_logging(force=
    caplog.set_level(logging.INFO, logger="erp")  # caplog.set_level(logging
    client = TestClient(create_app())  # client = TestClient(crea

    missing = client.get("/not-found", headers={"X-Request-ID": "trace-42"})  # missing = client.get('/n

    assert missing.status_code == 404  # assert missing.status_co
    assert "GET /not-found" in caplog.text  # assert 'GET /not-found' 
    assert "status=404" in caplog.text  # assert 'status=404' in c
    assert any(getattr(record, "request_id", None) == "trace-42" for record in caplog.records)  # assert any(getattr(recor


def test_health_check_is_not_logged_at_info(caplog):  # def test_health_check_is
    configure_logging(force=True, to_file=False)  # configure_logging(force=
    caplog.set_level(logging.INFO, logger="erp")  # caplog.set_level(logging
    client = TestClient(create_app())  # client = TestClient(crea
    caplog.clear()  # caplog.clear()

    response = client.get("/health", headers={"X-Request-ID": "health-1"})  # response = client.get('/

    assert response.status_code == 200  # assert response.status_c
    assert "GET /health" not in caplog.text  # assert 'GET /health' not


def test_domain_error_is_logged_as_warning(caplog):  # def test_domain_error_is
    configure_logging(force=True, to_file=False)  # configure_logging(force=
    caplog.set_level(logging.WARNING, logger="erp")  # caplog.set_level(logging
    app = create_app()  # app = create_app()
    router = APIRouter()  # router = APIRouter()

    @router.get("/boom")  # @router.get('/boom')
    def boom():  # def boom():
        raise AppError("INVENTORY_INSUFFICIENT", "库存不足", 409)  # raise AppError('INVENTOR

    app.include_router(router)  # app.include_router(route
    response = TestClient(app).get("/boom", headers={"X-Request-ID": "err-1"})  # response = TestClient(ap

    assert response.status_code == 409  # assert response.status_c
    assert response.json()["code"] == "INVENTORY_INSUFFICIENT"  # assert response.json()['
    assert "INVENTORY_INSUFFICIENT" in caplog.text  # assert 'INVENTORY_INSUFF
    assert any(getattr(record, "request_id", None) == "err-1" for record in caplog.records)  # assert any(getattr(recor


def test_unhandled_error_returns_internal_error_envelope(caplog):  # def test_unhandled_error
    configure_logging(force=True, to_file=False)  # configure_logging(force=
    caplog.set_level(logging.ERROR, logger="erp")  # caplog.set_level(logging
    app = create_app()  # app = create_app()
    router = APIRouter()  # router = APIRouter()

    @router.get("/crash")  # @router.get('/crash')
    def crash():  # def crash():
        raise RuntimeError("secret-db-url")  # raise RuntimeError('secr

    app.include_router(router)  # app.include_router(route
    response = TestClient(app, raise_server_exceptions=False).get("/crash")  # response = TestClient(ap

    assert response.status_code == 500  # assert response.status_c
    body = response.json()  # body = response.json()
    assert body["code"] == "INTERNAL_ERROR"  # assert body['code'] == '
    assert "secret-db-url" not in body["message"]  # assert 'secret-db-url' n
    assert "unhandled error" in caplog.text  # assert 'unhandled error'
