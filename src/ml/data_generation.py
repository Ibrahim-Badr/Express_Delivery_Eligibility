from pathlib import Path

import numpy as np
import pandas as pd

from src.etl.cleaning import compute_ground_truth_labels


def generate_orders_dataset(n_rows: int = 6000, random_state: int = 42) -> pd.DataFrame:
    """Generate a synthetic dataset representing e-commerce orders."""
    rng = np.random.default_rng(random_state)
    order_date = pd.date_range(start="2025-01-01", end="2025-12-31", periods=n_rows)
    hour = rng.integers(7, 23, size=n_rows)
    day_of_week = pd.Series(order_date).dt.dayofweek.to_numpy()
    weekend = (day_of_week >= 5).astype(int)

    data = pd.DataFrame(
        {
            "order_id": [f"CMD-{i:06d}" for i in range(1, n_rows + 1)],
            "order_date": order_date,
            "hour": hour,
            "day_of_week": day_of_week,
            "weekend": weekend,
            "distance_km": np.round(rng.gamma(shape=2.0, scale=4.0, size=n_rows), 2),
            "order_value_eur": np.round(rng.uniform(10, 250, size=n_rows), 2),
            "weight_kg": np.round(rng.uniform(0.2, 25, size=n_rows), 2),
            "stock_available": rng.binomial(1, 0.85, size=n_rows),
            "preparation_time_min": np.round(
                rng.normal(loc=25, scale=10, size=n_rows).clip(5, 90), 1
            ),
            "carrier_capacity": np.round(rng.uniform(0.2, 1.0, size=n_rows), 2),
            "weather": rng.choice(
                ["normal", "pluie", "neige", "orage"],
                size=n_rows,
                p=[0.65, 0.20, 0.10, 0.05],
            ),
            "delivery_zone": rng.choice(
                ["centre", "proche_banlieue", "banlieue", "rurale"],
                size=n_rows,
                p=[0.30, 0.30, 0.25, 0.15],
            ),
            "customer_type": rng.choice(
                ["standard", "premium"], size=n_rows, p=[0.80, 0.20]
            ),
        }
    )

    data["express_eligible"] = compute_ground_truth_labels(data, random_state=random_state)
    return data


if __name__ == "__main__":
    df = generate_orders_dataset()
    Path("data").mkdir(exist_ok=True)
    df.to_csv("data/raw_orders.csv", index=False)
    print("Dataset generated successfully at data/raw_orders.csv")
