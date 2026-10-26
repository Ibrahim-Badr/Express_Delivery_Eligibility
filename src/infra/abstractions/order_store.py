from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from src.domain.entities import OrderEntity


class OrderStore(ABC):
    @abstractmethod
    def save(self, order_id: str, order_data: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def get(self, order_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_training_data(self) -> tuple[list[OrderEntity], list[int]]:
        """Retrieve cleaned order entities and their binary target labels for training."""
        pass
