PROJECT_NAME = "eligibilite-livraison-express"
MODEL_VERSION = "1.0.0"
RANDOM_STATE = 42

FEATURE_COLUMNS = [
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
]

NUMERIC_FEATURES = [
    "hour",
    "day_of_week",
    "distance_km",
    "order_value_eur",
    "weight_kg",
    "preparation_time_min",
    "carrier_capacity",
]
CATEGORICAL_FEATURES = ["weather", "delivery_zone", "customer_type"]
PASSTHROUGH_FEATURES = ["weekend", "stock_available"]
