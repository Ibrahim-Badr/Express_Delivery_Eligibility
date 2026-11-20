from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class OrderMessageBroker(ABC):
    """Abstract port for live order streaming via a message broker (e.g. RabbitMQ)."""

    @abstractmethod
    def publish_order(self, order_data: Dict[str, Any]) -> None:
        """Publish an incoming order event to the live delivery queue."""
        raise NotImplementedError

    @abstractmethod
    def consume_orders(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        """Pull up to `max_messages` pending order payloads from the queue."""
        raise NotImplementedError
