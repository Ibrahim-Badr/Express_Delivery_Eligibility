import pandas as pd
import pytest

from src.api.schemas import OrderFeatures
from src.core.constants import FEATURE_COLUMNS
from src.domain.entities import OrderEntity
from src.etl.cleaning import (
    clean_orders_data,
    compute_ground_truth_labels,
    normalize_order_payload,
    validate_dataset,
)
from src.etl.features import orders_to_dataframe
from src.ml.data_generation import generate_orders_dataset


def test_validate_dataset_valid():
    df = generate_orders_dataset(n_rows=50, random_state=42)
    assert validate_dataset(df) is True


def test_validate_dataset_rejects_duplicates():
    df = generate_orders_dataset(n_rows=10, random_state=42)
    df_dup = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="Duplicate"):
        validate_dataset(df_dup)


def test_clean_orders_data_removes_duplicates_and_invalid_values():
    df = generate_orders_dataset(n_rows=20, random_state=42)
    dirty = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    dirty.loc[1, "distance_km"] = -5.0
    dirty.loc[2, "carrier_capacity"] = 1.5

    cleaned = clean_orders_data(dirty)
    assert len(cleaned) == 18
    assert validate_dataset(cleaned) is True


def test_orders_to_dataframe_preserves_feature_contract(sample_order_entity: OrderEntity):
    df = orders_to_dataframe([sample_order_entity])
    assert list(df.columns) == FEATURE_COLUMNS
    assert len(df) == 1
    assert "order_id" not in df.columns


def test_normalize_order_payload_bridges_erp_and_api_schemas(sample_order_dict):
    raw_erp = {
        "order_id": "ERP-00000042",
        "order_date": "2015-03-14",
        "hour": 11,
        "day_of_week": 5,
        "weekend": None,
        "distance_km": 9.5,
        "order_value_eur": 120.0,
        "weight_kg": 4.2,
        "stock_available": 1,
        "preparation_time_min": None,
        "carrier_capacity": 25.0,
        "weather": "rain",
        "delivery_zone": "suburb",
        "customer_type": "business",
    }
    normalized = normalize_order_payload(raw_erp)
    validated = OrderFeatures(**normalized)

    assert validated.order_id == "ERP-00000042"
    assert validated.weekend == 1
    assert validated.preparation_time_min == 20.0
    assert validated.carrier_capacity == 0.5
    assert validated.weather == "pluie"
    assert validated.delivery_zone == "banlieue"
    assert validated.customer_type == "premium"

    # Idempotent on canonical API payload
    api_normalized = normalize_order_payload(sample_order_dict)
    assert OrderFeatures(**api_normalized).weather == sample_order_dict["weather"]


def test_compute_ground_truth_labels_is_deterministic_across_row_shuffles():
    df = generate_orders_dataset(n_rows=40, random_state=42).drop(columns=["express_eligible"])
    labels_original = compute_ground_truth_labels(df, random_state=42)
    mapping_original = dict(zip(df["order_id"], labels_original))

    shuffled = df.sample(frac=1.0, random_state=99).reset_index(drop=True)
    labels_shuffled = compute_ground_truth_labels(shuffled, random_state=42)
    mapping_shuffled = dict(zip(shuffled["order_id"], labels_shuffled))

    assert mapping_original == mapping_shuffled


def test_clean_orders_data_preserves_mixed_erp_and_api_carrier_capacity():
    erp_rows = generate_orders_dataset(n_rows=30, random_state=42).drop(
        columns=["express_eligible"]
    )
    erp_rows["carrier_capacity"] = 35.0  # Raw ERP scale [5, 50]

    api_row = erp_rows.iloc[[0]].copy()
    api_row["order_id"] = "API-MIXED-01"
    api_row["carrier_capacity"] = 0.85  # Already-normalized API scale [0, 1]

    invalid_row = erp_rows.iloc[[1]].copy()
    invalid_row["order_id"] = "BAD-CAP-01"
    invalid_row["carrier_capacity"] = 1.5  # Invalid out-of-range value in (1, 5)

    mixed = pd.concat([erp_rows, api_row, invalid_row], ignore_index=True)
    cleaned = clean_orders_data(mixed)

    assert "BAD-CAP-01" not in set(cleaned["order_id"])
    api_cap = cleaned.loc[cleaned["order_id"] == "API-MIXED-01", "carrier_capacity"].iloc[0]
    erp_cap = cleaned.loc[cleaned["order_id"] == "CMD-000001", "carrier_capacity"].iloc[0]
    assert api_cap == pytest.approx(0.85)
    assert erp_cap == pytest.approx(0.70)
