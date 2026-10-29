from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.domain.entities import OrderEntity
from src.infra.abstractions.order_repository import OrderRepository


class OrderStore(OrderRepository):
    """Alias and backward-compatible abstract base class for OrderRepository."""

    def get_all(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        return []

    def count(self) -> int:
        return 0


__all__ = ["OrderStore", "OrderRepository", "OrderEntity"]
