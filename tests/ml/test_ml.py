import pytest

from src.domain.entities import OrderEntity
from src.ml.data_generation import generate_orders_dataset
from src.ml.pipeline import MLPipeline
from src.ml.predictor import MLPredict
from src.ml.training import MLTrainer, TrainTestSplitter
from tests.conftest import FakePipeline


def test_ml_predict_respects_threshold(sample_order_entity: OrderEntity):
    fake_pipeline = FakePipeline(positive_proba=0.65)

    pred_standard = MLPredict(pipeline=fake_pipeline, threshold=0.5).predict(sample_order_entity)
    assert pred_standard.express_eligible is True
    assert pred_standard.decision == "oui"
    assert pred_standard.probability == 0.65

    pred_strict = MLPredict(pipeline=fake_pipeline, threshold=0.75).predict(sample_order_entity)
    assert pred_strict.express_eligible is False
    assert pred_strict.decision == "non"


def test_train_test_splitter_validates_lengths(sample_order_entity: OrderEntity):
    splitter = TrainTestSplitter()
    with pytest.raises(ValueError, match="must match"):
        splitter.split([sample_order_entity], [1, 0])


def test_ml_trainer_fits_and_computes_metrics():
    df = generate_orders_dataset(n_rows=120, random_state=42)
    orders = [
        OrderEntity(
            order_id=row["order_id"],
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
        for row in df.to_dict(orient="records")
    ]
    labels = [int(x) for x in df["express_eligible"].tolist()]

    trainer = MLTrainer(model_pipeline=MLPipeline(random_seed=42).get_model_pipeline())
    _, metrics, y_pred, y_proba = trainer.train(orders, labels)

    assert set(metrics.keys()) == {"accuracy", "precision", "recall", "f1_score", "roc_auc"}
    assert 0.0 <= metrics["roc_auc"] <= 1.0
    assert len(y_pred) == 24
    assert len(y_proba) == 24
