from typing import Any, Dict

from fastapi.testclient import TestClient

from src.core.dependencies import (
    get_model_repository,
    get_order_store,
    get_prediction_store,
)
from src.infra.local.memory_order_store import MemoryOrderStore
from src.infra.local.memory_prediction_store import MemoryPredictionStore
from src.main import app
from tests.conftest import FakeModelRepository


def _create_client(model_available: bool = True) -> TestClient:
    model_repo = FakeModelRepository(available=model_available)
    order_store = MemoryOrderStore()
    pred_store = MemoryPredictionStore()
    app.dependency_overrides[get_model_repository] = lambda: model_repo
    app.dependency_overrides[get_order_store] = lambda: order_store
    app.dependency_overrides[get_prediction_store] = lambda: pred_store
    return TestClient(app)


def test_health_and_readiness_ok():
    client = _create_client(model_available=True)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
    app.dependency_overrides.clear()


def test_readiness_and_prediction_return_503_when_model_unavailable(
    sample_order_dict: Dict[str, Any],
):
    client = _create_client(model_available=False)
    ready = client.get("/health/ready")
    assert ready.status_code == 503
    assert ready.json()["status"] == "not_ready"

    pred = client.post("/v1/predictions", json=sample_order_dict)
    assert pred.status_code == 503
    app.dependency_overrides.clear()


def test_predictions_v1_and_root_predict_alias(sample_order_dict: Dict[str, Any]):
    client = _create_client(model_available=True)

    # POST /v1/predictions
    res = client.post("/v1/predictions", json=sample_order_dict)
    assert res.status_code == 200
    data = res.json()
    assert data["express_eligible"] is True
    assert data["decision"] == "oui"
    order_id = data["order_id"]

    # GET /v1/predictions/{order_id}
    hist = client.get(f"/v1/predictions/{order_id}")
    assert hist.status_code == 200
    assert hist.json()["order_id"] == order_id

    # POST /predict alias
    alias_res = client.post("/predict", json=sample_order_dict)
    assert alias_res.status_code == 200
    assert alias_res.json()["decision"] == "oui"

    # Batch predictions
    batch_res = client.post("/v1/predictions/batch", json={"orders": [sample_order_dict]})
    assert batch_res.status_code == 200
    assert batch_res.json()["count"] == 1
    app.dependency_overrides.clear()


def test_orders_and_model_card_endpoints(sample_order_dict: Dict[str, Any]):
    client = _create_client(model_available=True)

    order_res = client.post("/v1/orders", json=sample_order_dict)
    assert order_res.status_code == 202
    order_id = order_res.json()["order_id"]

    get_order = client.get(f"/v1/orders/{order_id}")
    assert get_order.status_code == 200
    assert get_order.json()["distance_km"] == sample_order_dict["distance_km"]

    model_res = client.get("/v1/model")
    assert model_res.status_code == 200
    assert model_res.json()["model_type"] == "LogisticRegression"
    app.dependency_overrides.clear()


def test_invalid_payload_returns_422(sample_order_dict: Dict[str, Any]):
    client = _create_client(model_available=True)
    bad_payload = dict(sample_order_dict)
    bad_payload["carrier_capacity"] = 2.5  # Must be <= 1.0

    res = client.post("/v1/predictions", json=bad_payload)
    assert res.status_code == 422
    app.dependency_overrides.clear()
