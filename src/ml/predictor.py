from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Dict

from src.core.config import settings
from src.domain.entities import OrderEntity, PredictionEntity
from src.etl.features import orders_to_dataframe


class MLPredict:
    """Executes eligibility predictions using a trained pipeline and configurable threshold."""

    def __init__(
        self,
        pipeline: Any,
        threshold: float | None = None,
        model_version: str | None = None,
    ):
        self.pipeline = pipeline
        self.threshold = threshold if threshold is not None else settings.model_threshold
        self.model_version = model_version or settings.model_version

    def predict(self, order: OrderEntity | Mapping[str, Any]) -> PredictionEntity:
        input_df = orders_to_dataframe([order])
        probability = float(self.pipeline.predict_proba(input_df)[0, 1])
        eligible = probability >= self.threshold
        decision = "oui" if eligible else "non"
        order_id = (
            order.order_id
            if isinstance(order, OrderEntity)
            else order.get("order_id")
        )

        return PredictionEntity(
            order_id=order_id,
            express_eligible=bool(eligible),
            decision=decision,
            probability=round(probability, 4),
            model_version=self.model_version,
            prediction_timestamp=datetime.now(timezone.utc).isoformat(),
        )


def predict_single_order(
    pipeline: Any,
    order_data: Dict[str, Any] | OrderEntity,
    threshold: float | None = None,
) -> Dict[str, Any]:
    """Helper that predicts a single order and returns a dictionary."""
    predictor = MLPredict(pipeline=pipeline, threshold=threshold)
    pred = predictor.predict(order_data)
    return {
        "express_eligible": pred.express_eligible,
        "decision": pred.decision,
        "probability": pred.probability,
        "model_version": pred.model_version,
        "prediction_timestamp": pred.prediction_timestamp,
    }
