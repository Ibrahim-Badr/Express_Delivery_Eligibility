import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends

from src.api.schemas import OrderAccepted, OrderFeatures, Prediction
from src.core.config import settings
from src.core.dependencies import (
    get_model_repository,
    get_order_repository,
    get_prediction_store,
)
from src.core.errors import NotFoundError
from src.infra.abstractions.model_repository import ModelRepository
from src.infra.abstractions.order_repository import OrderRepository
from src.infra.abstractions.prediction_store import PredictionStore
from src.ml.predictor import predict_single_order

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/orders", tags=["orders"])


def process_prediction_task(
    order_id: str,
    order_data: dict,
    model_repo: ModelRepository,
    pred_store: PredictionStore,
):
    """Execute background prediction for an accepted order and persist the result."""
    try:
        pipeline = model_repo.load_pipeline()
        start_time = datetime.now()
        pred_res = predict_single_order(pipeline, order_data)
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
    except Exception as exc:
        logger.error("Error during asynchronous prediction task for %s: %s", order_id, exc)


@router.post("", response_model=OrderAccepted, status_code=202)
async def create_order(
    order: OrderFeatures,
    background_tasks: BackgroundTasks,
    order_store: OrderRepository = Depends(get_order_repository),
    model_repo: ModelRepository = Depends(get_model_repository),
    pred_store: PredictionStore = Depends(get_prediction_store),
):
    order_id = order.order_id or f"CMD-{uuid.uuid4().hex[:6]}"
    order_dict = order.model_dump(exclude_none=True)
    order_dict["order_id"] = order_id

    order_store.save(order_id, order_dict)
    background_tasks.add_task(
        process_prediction_task, order_id, order_dict, model_repo, pred_store
    )

    return OrderAccepted(order_id=order_id, status="accepted")


@router.get("/{order_id}", response_model=OrderFeatures)
async def get_order(
    order_id: str, order_store: OrderRepository = Depends(get_order_repository)
):
    order = order_store.get(order_id)
    if not order:
        raise NotFoundError(f"Order {order_id} not found")
    return OrderFeatures(**order)
