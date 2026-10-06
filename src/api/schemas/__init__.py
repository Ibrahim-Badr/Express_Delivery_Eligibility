from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class OrderFeatures(BaseModel):
    order_id: Optional[str] = None
    hour: int = Field(..., ge=0, le=23)
    day_of_week: int = Field(..., ge=0, le=6)
    weekend: Literal[0, 1]
    distance_km: float = Field(..., ge=0.0)
    order_value_eur: float = Field(..., ge=0.0)
    weight_kg: float = Field(..., ge=0.0)
    stock_available: Literal[0, 1]
    preparation_time_min: float = Field(..., ge=0.0)
    carrier_capacity: float = Field(..., ge=0.0, le=1.0)
    weather: Literal["normal", "pluie", "neige", "orage"]
    delivery_zone: Literal["centre", "proche_banlieue", "banlieue", "rurale"]
    customer_type: Literal["standard", "premium"]
    
    model_config = {"extra": "forbid"}

class OrderAccepted(BaseModel):
    order_id: str
    status: Literal["accepted"]

class Prediction(BaseModel):
    order_id: str
    express_eligible: bool
    decision: Literal["oui", "non"]
    probability: float = Field(..., ge=0.0, le=1.0)
    model_version: str
    predicted_at: datetime
    latency_ms: Optional[float] = None

class BatchPredictionRequest(BaseModel):
    orders: List[OrderFeatures] = Field(..., min_length=1, max_length=1000)

class BatchPredictionResponse(BaseModel):
    predictions: List[Prediction]
    count: int

class ModelCard(BaseModel):
    project: str
    model_version: str
    model_type: str
    task: str
    target: str
    threshold: float
    trained_at: Optional[datetime] = None
    features: List[str]
    metrics: Dict[str, float]
    limitations: Optional[List[str]] = None

class HealthStatus(BaseModel):
    status: Literal["ok"]
    service: str
    version: str

class ReadinessStatus(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: Dict[str, str]
    version: Optional[str] = None

class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[List[str]] = None
