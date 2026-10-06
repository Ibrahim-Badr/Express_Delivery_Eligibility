from typing import Dict, Any, Optional
from src.infra.abstractions.order_store import OrderStore

class MemoryOrderStore(OrderStore):
    def __init__(self):
        self._orders: Dict[str, Dict[str, Any]] = {}

    def save(self, order_id: str, order_data: Dict[str, Any]) -> None:
        self._orders[order_id] = order_data

    def get(self, order_id: str) -> Optional[Dict[str, Any]]:
        return self._orders.get(order_id)
