import joblib
import json
from pathlib import Path
from typing import Dict, Any
from src.infra.abstractions.model_repository import ModelRepository

class FileModelRepository(ModelRepository):
    def __init__(self, artifacts_dir: str = "artifacts"):
        self.artifacts_dir = Path(artifacts_dir)
        self.pipeline_path = self.artifacts_dir / "pipeline.pkl"
        self.model_card_path = self.artifacts_dir / "model_card.json"
        
        self._pipeline = None
        self._model_card = None

    def is_available(self) -> bool:
        return self.pipeline_path.exists() and self.model_card_path.exists()

    def load_pipeline(self) -> Any:
        if self._pipeline is None:
            if not self.is_available():
                raise FileNotFoundError("Pipeline artifact not found.")
            self._pipeline = joblib.load(self.pipeline_path)
        return self._pipeline

    def load_model_card(self) -> Dict[str, Any]:
        if self._model_card is None:
            if not self.is_available():
                raise FileNotFoundError("Model card artifact not found.")
            with open(self.model_card_path, "r") as f:
                self._model_card = json.load(f)
        return self._model_card
