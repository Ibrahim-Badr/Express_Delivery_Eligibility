from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import joblib

from src.core.config import settings
from src.domain.entities import ModelEntity
from src.infra.abstractions.model_repository import ModelRepository


class FileModelRepository(ModelRepository):
    """Stores and loads ML model artifacts and metadata on the local filesystem."""

    def __init__(self, artifacts_dir: str | Path | None = None):
        self.artifacts_dir = Path(artifacts_dir or settings.artifacts_dir)
        self.model_joblib_path = self.artifacts_dir / "express_delivery_model.joblib"
        self.legacy_pipeline_path = self.artifacts_dir / "pipeline.pkl"
        self.model_card_path = self.artifacts_dir / "model_card.json"
        self.metrics_path = self.artifacts_dir / "metrics.json"
        self.features_path = self.artifacts_dir / "features.json"

        self._pipeline: Any = None
        self._model_card: Dict[str, Any] | None = None

    def _resolve_pipeline_path(self) -> Path | None:
        if self.model_joblib_path.exists():
            return self.model_joblib_path
        if self.legacy_pipeline_path.exists():
            return self.legacy_pipeline_path
        return None

    def is_available(self) -> bool:
        if self._pipeline is not None and self._model_card is not None:
            return True
        return self._resolve_pipeline_path() is not None and self.model_card_path.exists()

    def save(self, pipeline: Any, model_card: ModelEntity | Dict[str, Any]) -> None:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        card_dict = model_card.to_dict() if isinstance(model_card, ModelEntity) else dict(model_card)

        joblib.dump(pipeline, self.model_joblib_path)
        joblib.dump(pipeline, self.legacy_pipeline_path)

        self.model_card_path.write_text(json.dumps(card_dict, indent=2), encoding="utf-8")
        self.metrics_path.write_text(
            json.dumps(card_dict.get("metrics", {}), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        self.features_path.write_text(
            json.dumps(card_dict.get("features", []), indent=2),
            encoding="utf-8",
        )

        self._pipeline = pipeline
        self._model_card = card_dict

    def load_pipeline(self) -> Any:
        if self._pipeline is None:
            path = self._resolve_pipeline_path()
            if path is None:
                raise FileNotFoundError("Model pipeline artifact not found.")
            self._pipeline = joblib.load(path)
        return self._pipeline

    def load_model_card(self) -> Dict[str, Any]:
        if self._model_card is None:
            if not self.model_card_path.exists():
                raise FileNotFoundError("Model card artifact not found.")
            self._model_card = json.loads(self.model_card_path.read_text(encoding="utf-8"))
        return self._model_card
