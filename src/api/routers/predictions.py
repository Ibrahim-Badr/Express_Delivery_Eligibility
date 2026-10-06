from fastapi import APIRouter, Depends
from datetime import datetime, timezone
import uuid
from src.api.schemas import OrderFeatures, Prediction, BatchPredictionRequest, BatchPredictionResponse
from src.core.dependencies import get_model_repository
from src.infra.abstractions.model_repository import ModelRepository
from src.core.errors import ModelUnavailableError
from src.ml.predictor import predict_single_order
from src.core.constants import MODEL_VERSION

router = APIRouter(prefix="/v1/predictions", tags=["predictions"])

@router.post("", response_model=Prediction)
async def create_prediction(order: OrderFeatures, model_repo: ModelRepository = Depends(get_model_repository)):
    if not model_repo.is_available():
        raise ModelUnavailableError("Le modèle n'est pas disponible.")
    
    pipeline = model_repo.load_pipeline()
    order_id = order.order_id or f"CMD-{uuid.uuid4().hex[:6]}"
    order_dict = order.model_dump(exclude_none=True)
    order_dict["order_id"] = order_id
    
    start_time = datetime.now()
    pred_res = predict_single_order(pipeline, order_dict)
    latency = (datetime.now() - start_time).total_seconds() * 1000
    
    return Prediction(
        order_id=order_id,
        express_eligible=pred_res["express_eligible"],
        decision=pred_res["decision"],
        probability=pred_res["probability"],
        model_version=MODEL_VERSION,
        predicted_at=datetime.now(timezone.utc),
        latency_ms=round(latency, 2)
    )

@router.post("/batch", response_model=BatchPredictionResponse)
async def create_batch_predictions(batch: BatchPredictionRequest, model_repo: ModelRepository = Depends(get_model_repository)):
    if not model_repo.is_available():
        raise ModelUnavailableError("Le modèle n'est pas disponible.")
    
    pipeline = model_repo.load_pipeline()
    predictions = []
    
    for order in batch.orders:
        order_id = order.order_id or f"CMD-{uuid.uuid4().hex[:6]}"
        order_dict = order.model_dump(exclude_none=True)
        order_dict["order_id"] = order_id
        
        start_time = datetime.now()
        pred_res = predict_single_order(pipeline, order_dict)
        latency = (datetime.now() - start_time).total_seconds() * 1000
        
        predictions.append(Prediction(
            order_id=order_id,
            express_eligible=pred_res["express_eligible"],
            decision=pred_res["decision"],
            probability=pred_res["probability"],
            model_version=MODEL_VERSION,
            predicted_at=datetime.now(timezone.utc),
            latency_ms=round(latency, 2)
        ))
        
    return BatchPredictionResponse(predictions=predictions, count=len(predictions))
