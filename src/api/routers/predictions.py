import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends

from src.api.schemas import (
    BatchPredictionRequest,
    BatchPredictionResponse,
    OrderFeatures,
    Prediction,
)
from src.core.config import settings
from src.core.dependencies import get_model_repository, get_prediction_store
from src.core.errors import ModelUnavailableError, NotFoundError
from src.infra.abstractions.model_repository import ModelRepository
from src.infra.abstractions.prediction_store import PredictionStore
from src.ml.predictor import predict_single_order

router = APIRouter(prefix="/v1/predictions", tags=["predictions"])


def _execute_and_store_prediction(
    order: OrderFeatures,
    pipeline: Any,
    pred_store: PredictionStore,
) -> Prediction:
    """Compute prediction for an order, measure latency, and persist to PredictionStore."""
    order_id = order.order_id or f"CMD-{uuid.uuid4().hex[:6]}"
    order_dict = order.model_dump(exclude_none=True)
    order_dict["order_id"] = order_id

    start_time = datetime.now()
    pred_res = predict_single_order(pipeline, order_dict)
    latency = (datetime.now() - start_time).total_seconds() * 1000

    prediction = Prediction(
        order_id=order_id,
        express_eligible=pred_res["express_eligible"],
        decision=pred_res["decision"],
        probability=pred_res["probability"],
        model_version=settings.model_version,
        predicted_at=datetime.now(timezone.utc),
        latency_ms=round(latency, 2),
    )
    pred_store.save(order_id, prediction.model_dump(mode="json"))
    return prediction


@router.post("", response_model=Prediction)
async def create_prediction(
    order: OrderFeatures,
    model_repo: ModelRepository = Depends(get_model_repository),
    pred_store: PredictionStore = Depends(get_prediction_store),
):
    if not model_repo.is_available():
        raise ModelUnavailableError("The ML model is currently unavailable.")

    pipeline = model_repo.load_pipeline()
    return _execute_and_store_prediction(order, pipeline, pred_store)


@router.post("/batch", response_model=BatchPredictionResponse)
async def create_batch_predictions(
    batch: BatchPredictionRequest,
    model_repo: ModelRepository = Depends(get_model_repository),
    pred_store: PredictionStore = Depends(get_prediction_store),
):
    if not model_repo.is_available():
        raise ModelUnavailableError("The ML model is currently unavailable.")

    pipeline = model_repo.load_pipeline()
    predictions = [
        _execute_and_store_prediction(order, pipeline, pred_store)
        for order in batch.orders
    ]
    return BatchPredictionResponse(predictions=predictions, count=len(predictions))


@router.get("/{order_id}", response_model=Prediction)
async def get_prediction(
    order_id: str,
    pred_store: PredictionStore = Depends(get_prediction_store),
):
    prediction = pred_store.get(order_id)
    if not prediction:
        raise NotFoundError(f"Prediction for order {order_id} not found")
    return Prediction(**prediction)
