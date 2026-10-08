"""健康检查接口。"""

from fastapi.testclient import TestClient  # from fastapi.testclient 

from backend.app.main import app  # from backend.app.main im


def test_health_returns_ok():  # def test_health_returns_
    response = TestClient(app).get("/health")  # response = TestClient(ap

    assert response.status_code == 200  # assert response.status_c
    assert response.json() == {"status": "ok"}  # assert response.json() =
