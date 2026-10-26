from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class OrderEntity:
    """Immutable business entity representing an order."""

    hour: int
    day_of_week: int
    weekend: int
    distance_km: float
    order_value_eur: float
    weight_kg: float
    stock_available: int
    preparation_time_min: float
    carrier_capacity: float
    weather: str
    delivery_zone: str
    customer_type: str
    order_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PredictionEntity:
    """Immutable business result of an express delivery eligibility prediction."""

    express_eligible: bool
    decision: str
    probability: float
    model_version: str
    prediction_timestamp: str
    order_id: str | None = None
    latency_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModelEntity:
    """Model card metadata and evaluation metrics for the active model."""

    project: str
    model_version: str
    model_type: str
    task: str
    target: str
    threshold: float
    features: list[str]
    metrics: dict[str, float]
    trained_at: datetime | str | None = None
    limitations: list[str] = field(default_factory=lambda: ["Trained on synthetic data"])

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if isinstance(self.trained_at, datetime):
            data["trained_at"] = self.trained_at.isoformat()
        return data
