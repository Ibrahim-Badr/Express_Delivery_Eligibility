from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from src.core.config import settings
from src.domain.entities import OrderEntity
from src.etl.cleaning import clean_orders_data, validate_dataset
from src.infra.abstractions.order_store import OrderStore
from src.ml.data_generation import generate_orders_dataset


class MemoryOrderStore(OrderStore):
    def __init__(self, data_path: str | Path = "data/raw_orders.csv"):
        self._orders: Dict[str, Dict[str, Any]] = {}
        self._data_path = Path(data_path)

    def save(self, order_id: str, order_data: Dict[str, Any]) -> None:
        self._orders[order_id] = order_data

    def get(self, order_id: str) -> Optional[Dict[str, Any]]:
        return self._orders.get(order_id)

    def get_training_data(self) -> tuple[list[OrderEntity], list[int]]:
        if self._data_path.exists():
            df = pd.read_csv(self._data_path)
        else:
            df = generate_orders_dataset(random_state=settings.random_seed)
            self._data_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(self._data_path, index=False)

        df_clean = clean_orders_data(df)
        validate_dataset(df_clean)

        orders: list[OrderEntity] = []
        labels: list[int] = []
        for row in df_clean.to_dict(orient="records"):
            orders.append(
                OrderEntity(
                    order_id=str(row.get("order_id")) if row.get("order_id") is not None else None,
                    hour=int(row["hour"]),
                    day_of_week=int(row["day_of_week"]),
                    weekend=int(row["weekend"]),
                    distance_km=float(row["distance_km"]),
                    order_value_eur=float(row["order_value_eur"]),
                    weight_kg=float(row["weight_kg"]),
                    stock_available=int(row["stock_available"]),
                    preparation_time_min=float(row["preparation_time_min"]),
                    carrier_capacity=float(row["carrier_capacity"]),
                    weather=str(row["weather"]),
                    delivery_zone=str(row["delivery_zone"]),
                    customer_type=str(row["customer_type"]),
                )
            )
            labels.append(int(row["express_eligible"]))

        return orders, labels
