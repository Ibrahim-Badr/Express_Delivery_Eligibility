import uuid

from fastapi import APIRouter, BackgroundTasks, Depends

from src.api.schemas import OrderAccepted, OrderFeatures
from src.core.dependencies import get_model_repository, get_order_store
from src.core.errors import NotFoundError
from src.infra.abstractions.model_repository import ModelRepository
from src.infra.abstractions.order_store import OrderStore
from src.ml.predictor import predict_single_order

router = APIRouter(prefix="/v1/orders", tags=["orders"])


def process_prediction_task(
    order_id: str, order_data: dict, model_repo: ModelRepository
):
    try:
        pipeline = model_repo.load_pipeline()
        predict_single_order(pipeline, order_data)
    except Exception as exc:
        print(f"Error during asynchronous prediction task for {order_id}: {exc}")


@router.post("", response_model=OrderAccepted, status_code=202)
async def create_order(
    order: OrderFeatures,
    background_tasks: BackgroundTasks,
    order_store: OrderStore = Depends(get_order_store),
    model_repo: ModelRepository = Depends(get_model_repository),
):
    order_id = order.order_id or f"CMD-{uuid.uuid4().hex[:6]}"
    order_dict = order.model_dump(exclude_none=True)
    order_dict["order_id"] = order_id

    order_store.save(order_id, order_dict)
    background_tasks.add_task(
        process_prediction_task, order_id, order_dict, model_repo
    )

    return OrderAccepted(order_id=order_id, status="accepted")


@router.get("/{order_id}", response_model=OrderFeatures)
async def get_order(
    order_id: str, order_store: OrderStore = Depends(get_order_store)
):
    order = order_store.get(order_id)
    if not order:
        raise NotFoundError(f"Order {order_id} not found")
    return OrderFeatures(**order)
