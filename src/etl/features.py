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
    """Convert a sequence of OrderEntity objects or dicts into a DataFrame matching FEATURE_COLUMNS."""
    rows: list[dict[str, Any]] = []
    for order in orders:
        raw = order.to_dict() if isinstance(order, OrderEntity) else dict(order)
        rows.append({col: raw[col] for col in FEATURE_COLUMNS})
    return pd.DataFrame(rows, columns=FEATURE_COLUMNS)


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
