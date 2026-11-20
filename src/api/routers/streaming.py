from __future__ import annotations

import asyncio
import json
import random
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, StreamingResponse

from src.api.dashboard_ui import DASHBOARD_HTML
from src.api.schemas import OrderFeatures, Prediction
from src.core.config import settings
from src.core.dependencies import (
    get_message_broker,
    get_model_repository,
    get_order_repository,
    get_prediction_store,
)
from src.core.errors import ModelUnavailableError
from src.etl.cleaning import normalize_order_payload
from src.infra.abstractions.message_broker import OrderMessageBroker
from src.infra.abstractions.model_repository import ModelRepository
from src.infra.abstractions.order_repository import OrderRepository
from src.infra.abstractions.prediction_store import PredictionStore
from src.ml.predictor import predict_single_order

router = APIRouter(tags=["streaming"])

_RECENT_DELIVERIES: deque[Dict[str, Any]] = deque(maxlen=100)


def _compute_summary(deliveries: List[Dict[str, Any]]) -> Dict[str, int]:
    express_count = sum(1 for item in deliveries if item["decision"] == "oui")
    out_of_stock = sum(1 for item in deliveries if item["stock_available"] == 0)
    return {
        "total": len(deliveries),
        "express_count": express_count,
        "standard_count": len(deliveries) - express_count,
        "out_of_stock_count": out_of_stock,
    }


def _score_and_record_order(
    raw_order: Dict[str, Any],
    pipeline: Any,
    order_repo: OrderRepository,
    pred_store: PredictionStore,
) -> Dict[str, Any]:
    order_id = str(raw_order.get("order_id") or f"LIVE-{uuid.uuid4().hex[:6]}")
    enriched_raw = dict(raw_order)
    enriched_raw["order_id"] = order_id
    normalized = normalize_order_payload(enriched_raw)

    order_repo.save(order_id, enriched_raw)

    start_time = datetime.now()
    pred_res = predict_single_order(pipeline, normalized)
    latency = round((datetime.now() - start_time).total_seconds() * 1000, 2)

    prediction = Prediction(
        order_id=order_id,
        express_eligible=pred_res["express_eligible"],
        decision=pred_res["decision"],
        probability=pred_res["probability"],
        model_version=settings.model_version,
        predicted_at=datetime.now(timezone.utc),
        latency_ms=latency,
    )
    pred_store.save(order_id, prediction.model_dump(mode="json"))

    delivery_event: Dict[str, Any] = {
        **normalized,
        "order_id": order_id,
        "express_eligible": prediction.express_eligible,
        "decision": prediction.decision,
        "probability": prediction.probability,
        "model_version": prediction.model_version,
        "predicted_at": prediction.predicted_at.isoformat(),
        "latency_ms": prediction.latency_ms,
    }
    _RECENT_DELIVERIES.appendleft(delivery_event)
    return delivery_event


def _drain_and_score_orders(
    broker: OrderMessageBroker,
    model_repo: ModelRepository,
    order_repo: OrderRepository,
    pred_store: PredictionStore,
    max_messages: int = 20,
) -> List[Dict[str, Any]]:
    raw_orders = broker.consume_orders(max_messages=max_messages)
    if not raw_orders:
        return []
    if not model_repo.is_available():
        raise ModelUnavailableError("The ML model is currently unavailable.")

    pipeline = model_repo.load_pipeline()
    return [
        _score_and_record_order(raw_order, pipeline, order_repo, pred_store)
        for raw_order in raw_orders
    ]


@router.get("/v1/stream/deliveries/recent")
async def get_recent_deliveries(
    limit: int = 25,
    broker: OrderMessageBroker = Depends(get_message_broker),
    model_repo: ModelRepository = Depends(get_model_repository),
    order_repo: OrderRepository = Depends(get_order_repository),
    pred_store: PredictionStore = Depends(get_prediction_store),
):
    """Consume pending RabbitMQ orders, score eligibility, and return recent daily deliveries."""
    _drain_and_score_orders(broker, model_repo, order_repo, pred_store, max_messages=limit)
    items = list(_RECENT_DELIVERIES)[:limit]
    return {"deliveries": items, "summary": _compute_summary(list(_RECENT_DELIVERIES))}


@router.post("/v1/stream/simulate")
async def simulate_live_order(
    order: Optional[OrderFeatures] = None,
    broker: OrderMessageBroker = Depends(get_message_broker),
    model_repo: ModelRepository = Depends(get_model_repository),
    order_repo: OrderRepository = Depends(get_order_repository),
    pred_store: PredictionStore = Depends(get_prediction_store),
):
    """Publish a live order to RabbitMQ (pika) and immediately score it for demonstration."""
    if not model_repo.is_available():
        raise ModelUnavailableError("The ML model is currently unavailable.")

    if order is not None:
        raw_order = order.model_dump(exclude_none=True)
        raw_order["order_id"] = order.order_id or f"SIM-{uuid.uuid4().hex[:6].upper()}"
    else:
        now = datetime.now(timezone.utc)
        raw_order = {
            "order_id": f"SIM-{uuid.uuid4().hex[:6].upper()}",
            "order_date": now.date().isoformat(),
            "hour": now.hour,
            "day_of_week": now.weekday(),
            "weekend": int(now.weekday() >= 5),
            "distance_km": round(random.uniform(1.5, 22.0), 2),
            "order_value_eur": round(random.uniform(25.0, 220.0), 2),
            "weight_kg": round(random.uniform(0.5, 14.0), 2),
            "stock_available": random.choice([0, 1, 1, 1]),
            "preparation_time_min": round(random.uniform(8.0, 35.0), 1),
            "carrier_capacity": round(random.uniform(0.35, 0.95), 2),
            "weather": random.choice(["clear", "rain", "snow"]),
            "delivery_zone": random.choice(["centre", "suburb", "rural"]),
            "customer_type": random.choice(["individual", "business"]),
        }

    broker.publish_order(raw_order)
    scored = _drain_and_score_orders(
        broker, model_repo, order_repo, pred_store, max_messages=10
    )
    if scored:
        return scored[-1]
    pipeline = model_repo.load_pipeline()
    return _score_and_record_order(raw_order, pipeline, order_repo, pred_store)


@router.get("/v1/stream/deliveries")
async def stream_deliveries(
    poll_interval: float = 1.5,
    max_events: Optional[int] = None,
    broker: OrderMessageBroker = Depends(get_message_broker),
    model_repo: ModelRepository = Depends(get_model_repository),
    order_repo: OrderRepository = Depends(get_order_repository),
    pred_store: PredictionStore = Depends(get_prediction_store),
):
    """Stream newly scored RabbitMQ deliveries via Server-Sent Events (SSE)."""
    if not model_repo.is_available():
        raise ModelUnavailableError("The ML model is currently unavailable.")

    async def event_generator():
        sent = 0
        while max_events is None or sent < max_events:
            events = _drain_and_score_orders(
                broker, model_repo, order_repo, pred_store, max_messages=10
            )
            for event in events:
                yield f"data: {json.dumps(event)}\n\n"
                sent += 1
                if max_events is not None and sent >= max_events:
                    return
            if max_events is not None and not events:
                return
            await asyncio.sleep(poll_interval)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/dashboard", response_class=HTMLResponse)
async def get_logistics_dashboard():
    """Serve the interactive Logistics Operator Dashboard."""
    return HTMLResponse(content=DASHBOARD_HTML)
