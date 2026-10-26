from typing import Dict, Any, List, Optional
from src.infra.abstractions.prediction_store import PredictionStore

class MemoryPredictionStore(PredictionStore):
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    def save(self, order_id: str, prediction_data: Dict[str, Any]) -> None:
        self._store[order_id] = prediction_data

    def get(self, order_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get(order_id)

    def list_all(self) -> List[Dict[str, Any]]:
        return list(self._store.values())
