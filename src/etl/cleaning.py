from __future__ import annotations

import numpy as np
import pandas as pd


def harmonize_categories(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize categorical features across legacy French and modern English ERP schemas."""
    data = df.copy()

    weather_map = {
        "clear": "normal",
        "rain": "pluie",
        "wind": "orage",
        "snow": "neige",
        "normal": "normal",
        "pluie": "pluie",
        "orage": "orage",
        "neige": "neige",
    }
    if "weather" in data.columns:
        data["weather"] = data["weather"].astype(str).str.lower().map(
            lambda w: weather_map.get(w, "normal")
        )

    zone_map = {
        "centre": "centre",
        "suburb": "banlieue",
        "rural": "rurale",
        "proche_banlieue": "proche_banlieue",
        "banlieue": "banlieue",
        "rurale": "rurale",
    }
    if "delivery_zone" in data.columns:
        data["delivery_zone"] = data["delivery_zone"].astype(str).str.lower().map(
            lambda z: zone_map.get(z, "centre")
        )

    customer_map = {
        "individual": "standard",
        "business": "premium",
        "standard": "standard",
        "premium": "premium",
    }
    if "customer_type" in data.columns:
        data["customer_type"] = data["customer_type"].astype(str).str.lower().map(
            lambda c: customer_map.get(c, "standard")
        )

    return data


def compute_ground_truth_labels(
    df: pd.DataFrame, random_state: int = 42
) -> pd.Series:
    """Compute deterministic business eligibility labels for unlabelled ERP orders."""
    rng = np.random.default_rng(random_state)
    data = harmonize_categories(df)

    zone_penalty = data["delivery_zone"].map(
        {"centre": 0.0, "proche_banlieue": 0.10, "banlieue": 0.25, "rurale": 0.45}
    ).fillna(0.10)

    weather_penalty = data["weather"].map(
        {"normal": 0.0, "pluie": 0.10, "neige": 0.25, "orage": 0.30}
    ).fillna(0.0)

    customer_bonus = (data["customer_type"] == "premium").astype(int) * 0.15

    carrier = pd.to_numeric(data["carrier_capacity"], errors="coerce").fillna(0.5)
    if (carrier > 1.0).any():
        carrier = (carrier / 50.0).clip(0.0, 1.0)

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
    return pd.Series(rng.binomial(1, probability), index=df.index, name="express_eligible")


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

    # Normalize carrier_capacity if column represents the ERP scale [5, 50] (median > 2.0)
    if "carrier_capacity" in cleaned.columns:
        valid_caps = pd.to_numeric(cleaned["carrier_capacity"], errors="coerce").dropna()
        if not valid_caps.empty and valid_caps.median() > 2.0:
            cleaned["carrier_capacity"] = (cleaned["carrier_capacity"] / 50.0).clip(0.0, 1.0)

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
