from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd

from src.core.constants import FEATURE_COLUMNS

ERP_CARRIER_CAPACITY_MIN = 5.0
ERP_CARRIER_CAPACITY_MAX = 50.0

WEATHER_MAP = {
    "clear": "normal",
    "rain": "pluie",
    "wind": "orage",
    "snow": "neige",
    "normal": "normal",
    "pluie": "pluie",
    "orage": "orage",
    "neige": "neige",
}

ZONE_MAP = {
    "centre": "centre",
    "suburb": "banlieue",
    "rural": "rurale",
    "proche_banlieue": "proche_banlieue",
    "banlieue": "banlieue",
    "rurale": "rurale",
}

CUSTOMER_TYPE_MAP = {
    "individual": "standard",
    "business": "premium",
    "standard": "standard",
    "premium": "premium",
}


def parse_order_date(value: Any) -> date | None:
    """Parse a date, datetime, or ISO date string into a date object, or None."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.split("T")[0]).date()
        except ValueError:
            return None
    return None


def harmonize_categories(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize categorical features across legacy French and modern English ERP schemas."""
    data = df.copy()

    if "weather" in data.columns:
        data["weather"] = data["weather"].astype(str).str.lower().map(
            lambda w: WEATHER_MAP.get(w, "normal")
        )

    if "delivery_zone" in data.columns:
        data["delivery_zone"] = data["delivery_zone"].astype(str).str.lower().map(
            lambda z: ZONE_MAP.get(z, "centre")
        )

    if "customer_type" in data.columns:
        data["customer_type"] = data["customer_type"].astype(str).str.lower().map(
            lambda c: CUSTOMER_TYPE_MAP.get(c, "standard")
        )

    return data


def _normalize_carrier_capacity_series(series: pd.Series) -> pd.Series:
    """Scale ERP-range carrier_capacity [5, 50] to [0, 1] row-wise.

    Already-normalized values in [0, 1] are preserved unchanged; invalid values in
    (1, 5) remain unscaled so downstream sanity checks reject them.
    """
    numeric = pd.to_numeric(series, errors="coerce")
    erp_mask = numeric >= ERP_CARRIER_CAPACITY_MIN
    normalized = numeric.copy()
    normalized.loc[erp_mask] = (
        numeric.loc[erp_mask] / ERP_CARRIER_CAPACITY_MAX
    ).clip(0.0, 1.0)
    return normalized


def _deterministic_label(order_id: str, probability: float, seed: int = 42) -> int:
    """Derive a reproducible Bernoulli(probability) label keyed on (seed, order_id)."""
    digest = hashlib.sha256(f"{seed}:{order_id}".encode("utf-8")).digest()
    uniform = int.from_bytes(digest[:8], "big") / float(1 << 64)
    return int(uniform < probability)


def normalize_order_payload(raw_order: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a single raw ERP or stored order dict into the API/ML feature contract.

    - Imputes missing pre-2015 `weekend` from `day_of_week`.
    - Imputes missing pre-2017 `preparation_time_min` with 20.0.
    - Scales ERP `carrier_capacity` from [5, 50] down to [0.0, 1.0].
    - Harmonizes English ERP categories (`rain`, `suburb`, `business`) to French contract.
    - Projects strictly to `FEATURE_COLUMNS` (+ `order_id`) so `extra="forbid"` schemas succeed.
    """
    day_of_week = int(raw_order["day_of_week"])
    weekend_raw = raw_order.get("weekend")
    weekend = int(weekend_raw) if weekend_raw is not None else int(day_of_week >= 5)

    prep_raw = raw_order.get("preparation_time_min")
    prep_time = float(prep_raw) if prep_raw is not None else 20.0

    carrier_capacity = float(raw_order["carrier_capacity"])
    if carrier_capacity >= ERP_CARRIER_CAPACITY_MIN:
        carrier_capacity = round(
            min(max(carrier_capacity / ERP_CARRIER_CAPACITY_MAX, 0.0), 1.0), 4
        )

    normalized: dict[str, Any] = {
        "hour": int(raw_order["hour"]),
        "day_of_week": day_of_week,
        "weekend": weekend,
        "distance_km": float(raw_order["distance_km"]),
        "order_value_eur": float(raw_order["order_value_eur"]),
        "weight_kg": float(raw_order["weight_kg"]),
        "stock_available": int(raw_order["stock_available"]),
        "preparation_time_min": prep_time,
        "carrier_capacity": carrier_capacity,
        "weather": WEATHER_MAP.get(str(raw_order.get("weather", "")).lower(), "normal"),
        "delivery_zone": ZONE_MAP.get(str(raw_order.get("delivery_zone", "")).lower(), "centre"),
        "customer_type": CUSTOMER_TYPE_MAP.get(
            str(raw_order.get("customer_type", "")).lower(), "standard"
        ),
    }

    projected = {col: normalized[col] for col in FEATURE_COLUMNS}
    if raw_order.get("order_id") is not None:
        projected["order_id"] = str(raw_order["order_id"])
    return projected


def compute_ground_truth_labels(
    df: pd.DataFrame, random_state: int = 42
) -> pd.Series:
    """Compute order_id-deterministic eligibility labels for unlabelled ERP orders."""
    data = harmonize_categories(df)

    zone_penalty = data["delivery_zone"].map(
        {"centre": 0.0, "proche_banlieue": 0.10, "banlieue": 0.25, "rurale": 0.45}
    ).fillna(0.10)

    weather_penalty = data["weather"].map(
        {"normal": 0.0, "pluie": 0.10, "neige": 0.25, "orage": 0.30}
    ).fillna(0.0)

    customer_bonus = (data["customer_type"] == "premium").astype(int) * 0.15

    carrier = _normalize_carrier_capacity_series(data["carrier_capacity"]).fillna(0.5)

    prep_time = pd.to_numeric(data["preparation_time_min"], errors="coerce").fillna(20.0)
    weekend = pd.to_numeric(data["weekend"], errors="coerce").fillna(0)
    hour = pd.to_numeric(data["hour"], errors="coerce").fillna(12)
    dist = pd.to_numeric(data["distance_km"], errors="coerce").fillna(10.0)
    weight = pd.to_numeric(data["weight_kg"], errors="coerce").fillna(5.0)
    stock = pd.to_numeric(data["stock_available"], errors="coerce").fillna(1)

    score = (
        2.5
        - 0.18 * dist
        - 0.035 * prep_time
        - 0.035 * weight
        - zone_penalty
        - weather_penalty
        + 1.8 * stock
        + 1.3 * carrier
        + customer_bonus
        - 0.40 * weekend
        - 0.08 * np.maximum(hour - 18, 0)
    ).astype(float)

    probability = 1.0 / (1.0 + np.exp(-score.to_numpy(dtype=float)))
    if "order_id" in data.columns:
        order_ids = data["order_id"].astype(str).tolist()
    else:
        order_ids = [str(idx) for idx in df.index]

    labels = [
        _deterministic_label(order_id, float(prob), seed=random_state)
        for order_id, prob in zip(order_ids, probability)
    ]
    return pd.Series(labels, index=df.index, dtype=int, name="express_eligible")


def validate_dataset(df: pd.DataFrame) -> bool:
    """Perform elementary data quality checks on the input dataset."""
    required_columns = {
        "order_id",
        "order_date",
        "hour",
        "day_of_week",
        "weekend",
        "distance_km",
        "order_value_eur",
        "weight_kg",
        "stock_available",
        "preparation_time_min",
        "carrier_capacity",
        "weather",
        "delivery_zone",
        "customer_type",
        "express_eligible",
    }

    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    if df["order_id"].duplicated().any():
        raise ValueError("Duplicate order_id values found.")

    if df["express_eligible"].isna().any():
        raise ValueError("Target variable contains missing values.")

    if not df["hour"].between(0, 23).all():
        raise ValueError("Invalid hour values detected.")

    if not df["distance_km"].ge(0).all():
        raise ValueError("Distance cannot be negative.")

    if not df["weight_kg"].ge(0).all():
        raise ValueError("Weight cannot be negative.")

    if not df["preparation_time_min"].ge(0).all():
        raise ValueError("Preparation time cannot be negative.")

    if not df["carrier_capacity"].between(0, 1).all():
        raise ValueError("Carrier capacity must be between 0 and 1.")

    if not df["stock_available"].isin([0, 1]).all():
        raise ValueError("The stock_available variable must only contain 0 or 1.")

    return True


def clean_orders_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean raw order data and impute missing historical fields.

    Handles real-world schema evolutions and data anomalies:
    - Deduplication on order_id.
    - Imputation of missing `weekend` from day_of_week (pre-2015 migration).
    - Imputation of missing `preparation_time_min` using median (pre-2017 migration).
    - Normalization of `carrier_capacity` to [0, 1] range.
    - Categorical feature harmonization across ERP/French vocabularies.
    - Target label computation for unlabeled production ERP records.
    """
    cleaned = df.copy()

    # Deduplicate on business identifier
    if "order_id" in cleaned.columns:
        cleaned = cleaned.drop_duplicates(subset=["order_id"], keep="last")

    # Standardize order_date
    if "order_date" in cleaned.columns:
        cleaned["order_date"] = pd.to_datetime(cleaned["order_date"], errors="coerce")

    # Impute missing day_of_week if date is present
    if "day_of_week" not in cleaned.columns and "order_date" in cleaned.columns:
        cleaned["day_of_week"] = cleaned["order_date"].dt.dayofweek

    # Impute weekend (pre-July 2015 migration NULLs)
    if "weekend" in cleaned.columns:
        if cleaned["weekend"].isna().any() and "day_of_week" in cleaned.columns:
            cleaned["weekend"] = cleaned["weekend"].fillna(
                (cleaned["day_of_week"] >= 5).astype(int)
            )
    elif "day_of_week" in cleaned.columns:
        cleaned["weekend"] = (cleaned["day_of_week"] >= 5).astype(int)

    # Impute preparation_time_min (pre-July 2017 migration NULLs)
    if "preparation_time_min" in cleaned.columns:
        median_prep = cleaned["preparation_time_min"].median()
        if pd.isna(median_prep) or median_prep <= 0:
            median_prep = 20.0
        cleaned["preparation_time_min"] = cleaned["preparation_time_min"].fillna(median_prep)

    # Normalize ERP carrier_capacity [5, 50] to [0, 1] row-wise without corrupting API [0, 1] rows
    if "carrier_capacity" in cleaned.columns:
        cleaned["carrier_capacity"] = _normalize_carrier_capacity_series(
            cleaned["carrier_capacity"]
        )

    # Harmonize categories
    cleaned = harmonize_categories(cleaned)

    # Label orders if target is missing (production ERP feeds)
    if "express_eligible" not in cleaned.columns:
        cleaned["express_eligible"] = compute_ground_truth_labels(cleaned)
    else:
        # If target has NaNs, fill with ground truth calculation
        if cleaned["express_eligible"].isna().any():
            cleaned["express_eligible"] = cleaned["express_eligible"].fillna(
                compute_ground_truth_labels(cleaned)
            )

    # Ensure required fields are not NaN
    essential_columns = [
        "order_id",
        "distance_km",
        "weight_kg",
        "stock_available",
        "preparation_time_min",
        "carrier_capacity",
        "express_eligible",
    ]
    cleaned = cleaned.dropna(subset=[col for col in essential_columns if col in cleaned.columns])

    # Enforce numeric sanity
    cleaned = cleaned[cleaned["distance_km"] >= 0]
    cleaned = cleaned[cleaned["weight_kg"] >= 0]
    cleaned = cleaned[cleaned["preparation_time_min"] >= 0]
    cleaned = cleaned[cleaned["carrier_capacity"].between(0.0, 1.0)]
    cleaned = cleaned[cleaned["stock_available"].isin([0, 1])]
    cleaned["express_eligible"] = cleaned["express_eligible"].astype(int)

    return cleaned.reset_index(drop=True)
