from pathlib import Path
from typing import Any, Dict

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.domain.entities import ModelEntity
from src.infra.database.postgres_order_repository import PostgresOrderRepository
from src.infra.local.file_model_repository import FileModelRepository
from src.infra.local.memory_order_store import InMemoryOrderRepository, MemoryOrderStore
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
    assert store.count() == 1
    assert len(store.get_all()) == 1

    orders, labels = store.get_training_data()
    assert csv_path.exists()
    assert len(orders) == len(labels)
    assert len(orders) > 0


def test_in_memory_order_repository_alias():
    repo = InMemoryOrderRepository()
    assert isinstance(repo, MemoryOrderStore)


def test_postgres_order_repository_crud(sample_order_dict: Dict[str, Any]):
    test_engine = create_engine("sqlite:///:memory:")
    test_session = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    repo = PostgresOrderRepository(db_engine=test_engine, session_factory=test_session)

    assert repo.count() == 0
    assert repo.get("ERP-0001") is None

    repo.save("ERP-0001", sample_order_dict)
    assert repo.count() == 1

    fetched = repo.get("ERP-0001")
    assert fetched is not None
    assert fetched["order_id"] == "ERP-0001"
    assert fetched["distance_km"] == sample_order_dict["distance_km"]

    all_orders = repo.get_all()
    assert len(all_orders) == 1
    assert all_orders[0]["order_id"] == "ERP-0001"


def test_postgres_order_repository_migration_handling_and_training():
    test_engine = create_engine("sqlite:///:memory:")
    test_session = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    repo = PostgresOrderRepository(db_engine=test_engine, session_factory=test_session)

    # Legacy order simulating pre-2015 NULL weekend and pre-2017 NULL preparation_time
    legacy_order = {
        "order_id": "ERP-00000001",
        "order_date": "2015-03-15",
        "hour": 14,
        "day_of_week": 6,  # Sunday -> weekend should be imputed as 1
        "weekend": None,  # NULL migration
        "distance_km": 12.5,
        "order_value_eur": 85.0,
        "weight_kg": 3.2,
        "stock_available": 1,
        "preparation_time_min": None,  # NULL migration
        "carrier_capacity": 35.0,  # Range from ERP simulator [5, 50]
        "weather": "rain",  # English category from ERP
        "delivery_zone": "suburb",  # English category from ERP
        "customer_type": "business",  # English category from ERP
    }
    repo.save("ERP-00000001", legacy_order)

    orders, labels = repo.get_training_data()
    assert len(orders) == 1
    assert len(labels) == 1

    cleaned_entity = orders[0]
    assert cleaned_entity.order_id == "ERP-00000001"
    assert cleaned_entity.weekend == 1  # Successfully imputed from day_of_week >= 5
    assert cleaned_entity.preparation_time_min > 0  # Successfully imputed median
    assert 0.0 <= cleaned_entity.carrier_capacity <= 1.0  # Successfully normalized
    assert cleaned_entity.weather == "pluie"  # Harmonized category
    assert cleaned_entity.delivery_zone == "banlieue"  # Harmonized category
    assert cleaned_entity.customer_type == "premium"  # Harmonized category
    assert labels[0] in [0, 1]


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
