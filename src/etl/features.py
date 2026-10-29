from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.core.constants import (
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    NUMERIC_FEATURES,
    PASSTHROUGH_FEATURES,
)
from src.domain.entities import OrderEntity


def orders_to_dataframe(orders: Sequence[OrderEntity | Mapping[str, Any]]) -> pd.DataFrame:
    """Convert OrderEntity objects or dicts into a DataFrame matching FEATURE_COLUMNS."""
    rows: list[dict[str, Any]] = []
    for order in orders:
        raw = order.to_dict() if isinstance(order, OrderEntity) else dict(order)
        rows.append({col: raw[col] for col in FEATURE_COLUMNS})
    return pd.DataFrame(rows, columns=FEATURE_COLUMNS)


def dataframe_to_training_entities(df: pd.DataFrame) -> tuple[list[OrderEntity], list[int]]:
    """Convert a cleaned DataFrame with labels into OrderEntity objects and binary targets."""
    orders: list[OrderEntity] = []
    labels: list[int] = []
    for row in df.to_dict(orient="records"):
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


def get_preprocessor() -> ColumnTransformer:
    """Creates the data cleaning and feature engineering transformer."""
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, NUMERIC_FEATURES),
            ("cat", categorical_transformer, CATEGORICAL_FEATURES),
            ("pass", "passthrough", PASSTHROUGH_FEATURES),
        ]
    )

    return preprocessor
