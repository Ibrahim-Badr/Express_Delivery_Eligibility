from __future__ import annotations

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from src.core.config import settings
from src.etl.features import get_preprocessor


class MLPipeline:
    """Constructs the scikit-learn preprocessing and classification pipeline."""

    def __init__(self, random_seed: int | None = None):
        self.random_seed = random_seed if random_seed is not None else settings.random_seed

    def get_model_pipeline(self) -> Pipeline:
        return Pipeline(
            steps=[
                ("preprocessor", get_preprocessor()),
                (
                    "classifier",
                    LogisticRegression(
                        max_iter=1000,
                        class_weight="balanced",
                        random_state=self.random_seed,
                    ),
                ),
            ]
        )


def create_pipeline(random_seed: int | None = None) -> Pipeline:
    """Builds the complete scikit-learn pipeline (ETL + Model)."""
    return MLPipeline(random_seed=random_seed).get_model_pipeline()
