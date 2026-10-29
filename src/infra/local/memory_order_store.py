from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from src.core.config import settings
from src.domain.entities import OrderEntity
from src.etl.cleaning import clean_orders_data, validate_dataset
from src.etl.features import dataframe_to_training_entities
from src.infra.abstractions.order_repository import OrderRepository
from src.ml.data_generation import generate_orders_dataset


class MemoryOrderStore(OrderRepository):
    """In-memory order store and repository for local development and unit tests."""

    def __init__(self, data_path: str | Path = "data/raw_orders.csv"):
        self._orders: Dict[str, Dict[str, Any]] = {}
        self._data_path = Path(data_path)

    def save(self, order_id: str, order_data: Dict[str, Any]) -> None:
        self._orders[order_id] = order_data

    def get(self, order_id: str) -> Optional[Dict[str, Any]]:
        return self._orders.get(order_id)

    def get_all(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        orders = list(self._orders.values())
        if limit is not None:
            return orders[:limit]
        return orders

    def count(self) -> int:
        return len(self._orders)

    def get_training_data(self) -> tuple[list[OrderEntity], list[int]]:
        if self._data_path.exists():
            df = pd.read_csv(self._data_path)
        else:
            df = generate_orders_dataset(random_state=settings.random_seed)
            self._data_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(self._data_path, index=False)

        df_clean = clean_orders_data(df)
        validate_dataset(df_clean)
        return dataframe_to_training_entities(df_clean)


# Alias conforming to classroom architecture diagram
InMemoryOrderRepository = MemoryOrderStore

__all__ = ["MemoryOrderStore", "InMemoryOrderRepository"]
