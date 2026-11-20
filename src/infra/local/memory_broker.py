from __future__ import annotations

from collections import deque
from typing import Any, Dict, List

from src.infra.abstractions.message_broker import OrderMessageBroker


class MemoryOrderBroker(OrderMessageBroker):
    """In-memory message broker adapter for unit tests and local runs without RabbitMQ."""

    def __init__(self, maxlen: int = 1000):
        self._queue: deque[Dict[str, Any]] = deque(maxlen=maxlen)

    def publish_order(self, order_data: Dict[str, Any]) -> None:
        self._queue.append(dict(order_data))

    def consume_orders(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        drained: List[Dict[str, Any]] = []
        while self._queue and len(drained) < max_messages:
            drained.append(self._queue.popleft())
        return drained
