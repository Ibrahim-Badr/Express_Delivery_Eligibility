from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.domain.entities import OrderEntity


class OrderRepository(ABC):
    """Abstract contract for order persistence and retrieval.

    Follows Clean Architecture: domain and application layers depend solely
    on this interface without coupling to specific persistence mechanisms
    (PostgreSQL, MongoDB, In-Memory).
    """

    @abstractmethod
    def save(self, order_id: str, order_data: Dict[str, Any]) -> None:
        """Persist or update an order record by its unique business ID."""
        raise NotImplementedError

    @abstractmethod
    def get(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an order by its unique ID, or None if not found."""
        raise NotImplementedError

    @abstractmethod
    def get_all(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve all stored orders, optionally bounded by a limit."""
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        """Return the total number of orders in the store."""
        raise NotImplementedError

    @abstractmethod
    def get_training_data(self) -> tuple[list[OrderEntity], list[int]]:
        """Retrieve cleaned order entities and their binary target labels for ML training."""
        raise NotImplementedError
