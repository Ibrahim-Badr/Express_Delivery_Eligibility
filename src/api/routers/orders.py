from fastapi import APIRouter, Depends, BackgroundTasks
import uuid
from src.api.schemas import OrderFeatures, OrderAccepted
from src.core.dependencies import get_order_store, get_model_repository
from src.infra.abstractions.order_store import OrderStore
from src.infra.abstractions.model_repository import ModelRepository
from src.core.errors import NotFoundError
from src.ml.predictor import predict_single_order

router = APIRouter(prefix="/v1/orders", tags=["orders"])

def process_prediction_task(order_id: str, order_data: dict, model_repo: ModelRepository):
    try:
        pipeline = model_repo.load_pipeline()
        predict_single_order(pipeline, order_data)
    except Exception as e:
        print(f"Erreur lors de la prediction asynchrone: {e}")

@router.post("", response_model=OrderAccepted, status_code=202)
async def create_order(
    order: OrderFeatures,
    background_tasks: BackgroundTasks,
    order_store: OrderStore = Depends(get_order_store),
    model_repo: ModelRepository = Depends(get_model_repository)
):
    order_id = order.order_id or f"CMD-{uuid.uuid4().hex[:6]}"
    order_dict = order.model_dump(exclude_none=True)
    order_dict["order_id"] = order_id
    
    order_store.save(order_id, order_dict)
    
    background_tasks.add_task(process_prediction_task, order_id, order_dict, model_repo)
    
    return OrderAccepted(order_id=order_id, status="accepted")

@router.get("/{order_id}", response_model=OrderFeatures)
async def get_order(order_id: str, order_store: OrderStore = Depends(get_order_store)):
    order = order_store.get(order_id)
    if not order:
        raise NotFoundError(f"Commande {order_id} introuvable")
    return OrderFeatures(**order)
