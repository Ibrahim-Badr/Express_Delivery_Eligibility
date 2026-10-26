from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.core.config import settings
from src.domain.entities import ModelEntity


def compute_classification_metrics(y_true: Any, y_pred: Any, y_proba: Any) -> dict[str, float]:
    """Compute binary classification evaluation metrics."""
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1_score": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_proba)), 4),
    }


def evaluate_model(pipeline: Any, X_test: Any, y_test: Any) -> dict[str, Any]:
    """Evaluates the model and returns a Model Card dictionary."""
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]
    metrics = compute_classification_metrics(y_test, y_pred, y_proba)

    card = ModelEntity(
        project=settings.app_name,
        model_version=settings.model_version,
        model_type="LogisticRegression",
        task="binary classification",
        target="express_eligible",
        threshold=settings.model_threshold,
        features=list(X_test.columns),
        metrics=metrics,
        trained_at=datetime.now(timezone.utc),
        limitations=["Trained on synthetic data"],
    )
    return card.to_dict()
