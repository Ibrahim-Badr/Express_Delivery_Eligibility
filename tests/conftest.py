from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pytest

from src.domain.entities import ModelEntity, OrderEntity
from src.infra.abstractions.model_repository import ModelRepository


class FakePipeline:
    """Lightweight fake scikit-learn pipeline for fast unit and API tests."""

    def __init__(self, positive_proba: float = 0.85):
        self.positive_proba = positive_proba
        self.fitted = False

    def fit(self, X: Any, y: Any) -> "FakePipeline":
        self.fitted = True
        return self

    def predict(self, X: Any) -> np.ndarray:
        pred = 1 if self.positive_proba >= 0.5 else 0
        return np.full(len(X), pred, dtype=int)

    def predict_proba(self, X: Any) -> np.ndarray:
        p1 = self.positive_proba
        p0 = 1.0 - p1
        return np.tile([p0, p1], (len(X), 1))


class FakeModelRepository(ModelRepository):
    """In-memory ModelRepository double for isolated API testing."""

    def __init__(self, available: bool = True, positive_proba: float = 0.85):
        self.available = available
        self._pipeline: Any = FakePipeline(positive_proba=positive_proba) if available else None
        self._card: Dict[str, Any] = {
            "project": "eligibilite-livraison-express",
            "model_version": "1.0.0",
            "model_type": "LogisticRegression",
            "task": "binary classification",
            "target": "express_eligible",
            "threshold": 0.5,
            "features": [
                "hour",
                "day_of_week",
                "weekend",
                "distance_km",
                "order_value_eur",
                "weight_kg",
                "stock_available",
                "preparation_time_min",
                "carrier_capacity",
                "weather",
                "delivery_zone",
                "customer_type",
            ],
            "metrics": {
                "accuracy": 0.9,
                "precision": 0.88,
                "recall": 0.92,
                "f1_score": 0.9,
                "roc_auc": 0.95,
            },
            "limitations": ["Trained on synthetic data"],
        }

    def save(self, pipeline: Any, model_card: ModelEntity | Dict[str, Any]) -> None:
        self._pipeline = pipeline
        self._card = (
            model_card.to_dict() if isinstance(model_card, ModelEntity) else dict(model_card)
        )
        self.available = True

    def load_pipeline(self) -> Any:
        if not self.available or self._pipeline is None:
            raise FileNotFoundError("Fake model unavailable")
        return self._pipeline

    def load_model_card(self) -> Dict[str, Any]:
        if not self.available:
            raise FileNotFoundError("Fake model card unavailable")
        return self._card

    def is_available(self) -> bool:
        return self.available


@pytest.fixture
def sample_order_dict() -> Dict[str, Any]:
    return {
        "hour": 14,
        "day_of_week": 2,
        "weekend": 0,
        "distance_km": 3.5,
        "order_value_eur": 89.9,
        "weight_kg": 2.4,
        "stock_available": 1,
        "preparation_time_min": 18.0,
        "carrier_capacity": 0.85,
        "weather": "normal",
        "delivery_zone": "centre",
        "customer_type": "premium",
    }


@pytest.fixture
def sample_order_entity(sample_order_dict: Dict[str, Any]) -> OrderEntity:
    return OrderEntity(**sample_order_dict)
