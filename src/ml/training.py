from __future__ import annotations

import logging
import time
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sklearn.model_selection import train_test_split

from src.core.config import settings
from src.core.constants import FEATURE_COLUMNS
from src.domain.entities import ModelEntity, OrderEntity
from src.etl.features import orders_to_dataframe
from src.infra.abstractions.model_repository import ModelRepository
from src.infra.abstractions.order_store import OrderStore
from src.ml.evaluation import compute_classification_metrics
from src.ml.pipeline import MLPipeline

logger = logging.getLogger(__name__)


class TrainTestSplitter:
    """Validates order/label alignment and performs a stratified train/test split."""

    def __init__(self, test_size: float = 0.2, random_state: int | None = None):
        self.test_size = test_size
        self.random_state = random_state if random_state is not None else settings.random_seed

    def split(
        self,
        orders: Sequence[OrderEntity],
        labels: Sequence[int],
    ) -> tuple[Any, Any, list[int], list[int]]:
        if len(orders) != len(labels):
            raise ValueError(
                f"Orders count ({len(orders)}) must match labels count ({len(labels)})."
            )
        if not orders:
            raise ValueError("Cannot split an empty dataset.")

        X = orders_to_dataframe(orders)
        y = list(labels)
        stratify = y if len(set(y)) > 1 else None

        return train_test_split(
            X,
            y,
            test_size=self.test_size,
            random_state=self.random_state,
            stratify=stratify,
        )


class MLTrainer:
    """Trains the ML pipeline, logs to MLflow if available, and returns metrics."""

    def __init__(self, model_pipeline: Any = None):
        self.model_pipeline = model_pipeline or MLPipeline().get_model_pipeline()

    def train(
        self,
        orders: Sequence[OrderEntity],
        labels: Sequence[int],
        data_splitter: TrainTestSplitter | None = None,
    ) -> tuple[str | None, dict[str, float], Any, Any]:
        started_at = time.perf_counter()
        splitter = data_splitter or TrainTestSplitter()
        X_train, X_test, y_train, y_test = splitter.split(orders, labels)

        self.model_pipeline.fit(X_train, y_train)
        y_pred = self.model_pipeline.predict(X_test)
        y_proba = self.model_pipeline.predict_proba(X_test)[:, 1]
        metrics = compute_classification_metrics(y_test, y_pred, y_proba)

        run_id = self._log_to_mlflow(metrics)
        logger.info(
            "ML training completed (run_id=%s, duration=%.2f s, roc_auc=%.4f)",
            run_id,
            time.perf_counter() - started_at,
            metrics["roc_auc"],
        )
        return run_id, metrics, y_pred, y_proba

    def _log_to_mlflow(self, metrics: dict[str, float]) -> str | None:
        try:
            import mlflow
            import mlflow.sklearn

            if settings.mlflow_tracking_uri:
                if settings.mlflow_tracking_uri.startswith("sqlite:///"):
                    db_path = settings.mlflow_tracking_uri.replace("sqlite:///", "")
                    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
                mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
            mlflow.set_experiment(settings.mlflow_experiment_name)

            with mlflow.start_run(run_name="logistic-regression-baseline") as run:
                mlflow.log_param("model_type", "LogisticRegression")
                mlflow.log_param("random_state", settings.random_seed)
                mlflow.log_param("feature_count", len(FEATURE_COLUMNS))
                for metric_name, metric_value in metrics.items():
                    mlflow.log_metric(metric_name, metric_value)
                mlflow.sklearn.log_model(
                    self.model_pipeline,
                    name="model",
                    skops_trusted_types=["numpy.dtype"],
                )
                return run.info.run_id
        except Exception as exc:
            logger.warning("MLflow tracking skipped: %s", exc)
            return None


def train(
    order_store: OrderStore | None = None,
    model_repo: ModelRepository | None = None,
) -> ModelEntity:
    """End-to-end training job using OrderStore and ModelRepository abstractions."""
    from src.core.dependencies import get_model_repository, get_order_store

    store = order_store or get_order_store()
    repo = model_repo or get_model_repository()

    orders, labels = store.get_training_data()
    trainer = MLTrainer()
    _, metrics, _, _ = trainer.train(orders, labels)

    model_card = ModelEntity(
        project=settings.app_name,
        model_version=settings.model_version,
        model_type="LogisticRegression",
        task="binary classification",
        target="express_eligible",
        threshold=settings.model_threshold,
        features=list(FEATURE_COLUMNS),
        metrics=metrics,
        trained_at=datetime.now(timezone.utc),
        limitations=["Trained on synthetic data"],
    )
    repo.save(trainer.model_pipeline, model_card)
    logger.info("Training complete. Model and metadata saved via ModelRepository.")
    return model_card


if __name__ == "__main__":
    train()
