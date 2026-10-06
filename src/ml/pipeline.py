from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from src.etl.features import get_preprocessor
from src.core.constants import RANDOM_STATE

def create_pipeline() -> Pipeline:
    """Builds the complete scikit-learn pipeline (ETL + Model)."""
    return Pipeline(steps=[
        ("preprocessor", get_preprocessor()),
        ("classifier", LogisticRegression(random_state=RANDOM_STATE))
    ])
