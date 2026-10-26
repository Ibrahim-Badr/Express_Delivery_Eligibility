from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class PredictionStore(ABC):
    @abstractmethod
    def save(self, order_id: str, prediction_data: Dict[str, Any]) -> None:
        """Save a prediction result."""
        pass

    @abstractmethod
    def get(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a prediction by its order ID."""
        pass

    @abstractmethod
    def list_all(self) -> List[Dict[str, Any]]:
        """List all stored predictions."""
        pass
