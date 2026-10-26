from pathlib import Path
from typing import Any, Dict

from src.domain.entities import ModelEntity
from src.infra.local.file_model_repository import FileModelRepository
from src.infra.local.memory_order_store import MemoryOrderStore
from src.infra.local.memory_prediction_store import MemoryPredictionStore
from tests.conftest import FakePipeline


def test_memory_order_store_crud_and_training_data(
    tmp_path: Path, sample_order_dict: Dict[str, Any]
):
    csv_path = tmp_path / "orders.csv"
    store = MemoryOrderStore(data_path=csv_path)

    store.save("CMD-001", sample_order_dict)
    assert store.get("CMD-001") == sample_order_dict
    assert store.get("UNKNOWN") is None

    orders, labels = store.get_training_data()
    assert csv_path.exists()
    assert len(orders) == len(labels)
    assert len(orders) > 0


def test_memory_prediction_store_contract():
    store = MemoryPredictionStore()
    payload = {"order_id": "CMD-001", "express_eligible": True, "decision": "oui"}
    store.save("CMD-001", payload)

    assert store.get("CMD-001") == payload
    assert store.get("MISSING") is None
    assert len(store.list_all()) == 1


def test_file_model_repository_save_and_load(tmp_path: Path):
    repo = FileModelRepository(artifacts_dir=tmp_path)
    assert repo.is_available() is False

    card = ModelEntity(
        project="eligibilite-livraison-express",
        model_version="1.0.0",
        model_type="LogisticRegression",
        task="binary classification",
        target="express_eligible",
        threshold=0.5,
        features=["distance_km", "weight_kg"],
        metrics={"accuracy": 0.91, "roc_auc": 0.94},
    )
    pipeline = FakePipeline(positive_proba=0.8)
    repo.save(pipeline, card)

    assert repo.is_available() is True
    assert (tmp_path / "express_delivery_model.joblib").exists()
    assert (tmp_path / "metrics.json").exists()
    assert (tmp_path / "features.json").exists()
    assert (tmp_path / "model_card.json").exists()

    loaded_card = repo.load_model_card()
    assert loaded_card["metrics"]["roc_auc"] == 0.94
