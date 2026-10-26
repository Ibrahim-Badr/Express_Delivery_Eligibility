import pandas as pd


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
        raise ValueError(
            "Carrier capacity must be between 0 and 1."
        )

    if not df["stock_available"].isin([0, 1]).all():
        raise ValueError(
            "The stock_available variable must only contain 0 or 1."
        )

    return True


def clean_orders_data(df: pd.DataFrame) -> pd.DataFrame:
    """Automatically clean raw order data."""
    cleaned = df.copy()

    # Remove duplicates on the business identifier
    cleaned = cleaned.drop_duplicates(
        subset=["order_id"],
        keep="last",
    )

    # Convert date strings to datetime
    cleaned["order_date"] = pd.to_datetime(
        cleaned["order_date"],
        errors="coerce",
    )

    # Drop rows with missing essential fields
    essential_columns = [
        "order_id",
        "distance_km",
        "weight_kg",
        "stock_available",
        "preparation_time_min",
        "carrier_capacity",
        "express_eligible",
    ]

    cleaned = cleaned.dropna(subset=essential_columns)

    # Enforce numeric bounds
    cleaned = cleaned[cleaned["distance_km"] >= 0]
    cleaned = cleaned[cleaned["weight_kg"] >= 0]
    cleaned = cleaned[cleaned["preparation_time_min"] >= 0]
    cleaned = cleaned[cleaned["carrier_capacity"].between(0, 1)]
    cleaned = cleaned[cleaned["stock_available"].isin([0, 1])]

    return cleaned.reset_index(drop=True)
