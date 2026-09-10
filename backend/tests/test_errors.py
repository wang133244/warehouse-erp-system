from fastapi import APIRouter, HTTPException
from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_request_id_is_returned_for_success_and_not_found_response():
    app = create_app()
    client = TestClient(app)

    healthy = client.get("/health", headers={"X-Request-ID": "trace-42"})
    missing = client.get("/not-found", headers={"X-Request-ID": "trace-42"})

    assert healthy.headers["X-Request-ID"] == "trace-42"
    assert missing.headers["X-Request-ID"] == "trace-42"
    assert missing.json()["code"] == "NOT_FOUND"
    assert missing.json()["request_id"] == "trace-42"


def test_domain_error_uses_stable_envelope():
    app = create_app()
    router = APIRouter()

    @router.get("/inventory-error")
    def inventory_error():
        raise HTTPException(status_code=409, detail={"code": "INVENTORY_INSUFFICIENT", "message": "可用库存不足"})

    app.include_router(router)
    response = TestClient(app).get("/inventory-error")

    assert response.status_code == 409
    assert response.json()["code"] == "INVENTORY_INSUFFICIENT"
    assert response.json()["message"] == "可用库存不足"
    assert response.json()["request_id"]