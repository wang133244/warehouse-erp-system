"""AppError 与 HTTP 错误形态。"""

from fastapi import APIRouter, HTTPException  # from fastapi import APIR
from fastapi.testclient import TestClient  # from fastapi.testclient 

from backend.app.main import create_app  # from backend.app.main im


def test_request_id_is_returned_for_success_and_not_found_response():  # def test_request_id_is_r
    app = create_app()  # app = create_app()
    client = TestClient(app)  # client = TestClient(app)

    healthy = client.get("/health", headers={"X-Request-ID": "trace-42"})  # healthy = client.get('/h
    missing = client.get("/not-found", headers={"X-Request-ID": "trace-42"})  # missing = client.get('/n

    assert healthy.headers["X-Request-ID"] == "trace-42"  # assert healthy.headers['
    assert missing.headers["X-Request-ID"] == "trace-42"  # assert missing.headers['
    assert missing.json()["code"] == "NOT_FOUND"  # assert missing.json()['c
    assert missing.json()["request_id"] == "trace-42"  # assert missing.json()['r


def test_domain_error_uses_stable_envelope():  # def test_domain_error_us
    app = create_app()  # app = create_app()
    router = APIRouter()  # router = APIRouter()

    @router.get("/inventory-error")  # @router.get('/inventory-
    def inventory_error():  # def inventory_error():
        raise HTTPException(status_code=409, detail={"code": "INVENTORY_INSUFFICIENT", "message": "库存不足"})  # raise HTTPException(stat

    app.include_router(router)  # app.include_router(route
    response = TestClient(app).get("/inventory-error")  # response = TestClient(ap

    assert response.status_code == 409  # assert response.status_c
    assert response.json()["code"] == "INVENTORY_INSUFFICIENT"  # assert response.json()['
    assert response.json()["message"] == "库存不足"  # assert response.json()['
    assert response.json()["request_id"]  # assert response.json()['
