from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, String

from src.infra.abstractions.prediction_store import PredictionStore
from src.infra.database.database import Base, SessionLocal, engine


class PredictionRecord(Base):
    __tablename__ = "predictions"

    order_id = Column(String, primary_key=True, index=True)
    express_eligible = Column(Boolean, nullable=False)
    decision = Column(String, nullable=False)
    probability = Column(Float, nullable=False)
    model_version = Column(String, nullable=False)
    predicted_at = Column(DateTime, nullable=False)
    latency_ms = Column(Float, nullable=True)
    full_data = Column(JSON, nullable=False)


class PostgresPredictionStore(PredictionStore):
    def __init__(self):
        Base.metadata.create_all(bind=engine)
        self.SessionLocal = SessionLocal

    def save(self, order_id: str, prediction_data: Dict[str, Any]) -> None:
        db = self.SessionLocal()
        try:
            predicted_at = prediction_data.get("predicted_at")
            if isinstance(predicted_at, str):
                predicted_at = datetime.fromisoformat(predicted_at.replace("Z", "+00:00"))

            record = PredictionRecord(
                order_id=order_id,
                express_eligible=prediction_data["express_eligible"],
                decision=prediction_data["decision"],
                probability=prediction_data["probability"],
                model_version=prediction_data["model_version"],
                predicted_at=predicted_at,
                latency_ms=prediction_data.get("latency_ms"),
                full_data=prediction_data,
            )
            db.merge(record)
            db.commit()
        finally:
            db.close()

    def get(self, order_id: str) -> Optional[Dict[str, Any]]:
        db = self.SessionLocal()
        try:
            record = (
                db.query(PredictionRecord)
                .filter(PredictionRecord.order_id == order_id)
                .first()
            )
            if record:
                return record.full_data
            return None
        finally:
            db.close()

    def list_all(self) -> List[Dict[str, Any]]:
        db = self.SessionLocal()
        try:
            records = db.query(PredictionRecord).all()
            return [record.full_data for record in records]
        finally:
            db.close()
