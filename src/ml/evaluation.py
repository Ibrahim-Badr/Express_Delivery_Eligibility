from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from src.core.constants import PROJECT_NAME, MODEL_VERSION

def evaluate_model(pipeline, X_test, y_test) -> dict:
    """Evaluates the model and returns a Model Card dictionary."""
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred), 4),
        "recall": round(recall_score(y_test, y_pred), 4),
        "f1_score": round(f1_score(y_test, y_pred), 4),
        "roc_auc": round(roc_auc_score(y_test, y_proba), 4)
    }

    model_card = {
        "project": PROJECT_NAME,
        "model_version": MODEL_VERSION,
        "model_type": "Logistic regression",
        "task": "binary classification",
        "target": "express_eligible",
        "threshold": 0.5,
        "features": list(X_test.columns),
        "metrics": metrics,
        "limitations": ["Trained on synthetic data"]
    }
    return model_card
