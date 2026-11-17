from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

import joblib

from src.core.config import settings
from src.domain.entities import ModelEntity
from src.infra.abstractions.model_repository import ModelRepository


class FileModelRepository(ModelRepository):
    """Stores, loads, and hot-reloads ML model artifacts on the local filesystem."""

    def __init__(self, artifacts_dir: str | Path | None = None):
        self.artifacts_dir = Path(artifacts_dir or settings.artifacts_dir)
        self.model_joblib_path = self.artifacts_dir / "express_delivery_model.joblib"
        self.model_card_path = self.artifacts_dir / "model_card.json"
        self.metrics_path = self.artifacts_dir / "metrics.json"
        self.features_path = self.artifacts_dir / "features.json"

        self._pipeline: Any = None
        self._pipeline_mtime: float | None = None
        self._model_card: Dict[str, Any] | None = None
        self._card_mtime: float | None = None

    def is_available(self) -> bool:
        return self.model_joblib_path.exists() and self.model_card_path.exists()

    def save(self, pipeline: Any, model_card: ModelEntity | Dict[str, Any]) -> None:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        card_dict = (
            model_card.to_dict() if isinstance(model_card, ModelEntity) else dict(model_card)
        )

        joblib.dump(pipeline, self.model_joblib_path)

        self.model_card_path.write_text(json.dumps(card_dict, indent=2), encoding="utf-8")
        self.metrics_path.write_text(
            json.dumps(card_dict.get("metrics", {}), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        self.features_path.write_text(
            json.dumps(card_dict.get("features", []), indent=2),
            encoding="utf-8",
        )

        # Ensure group-writable permissions across shared Docker volumes (appuser + airflow)
        for path in (
            self.model_joblib_path,
            self.model_card_path,
            self.metrics_path,
            self.features_path,
        ):
            try:
                os.chmod(path, 0o664)
            except OSError:
                pass

        self._pipeline = pipeline
        self._pipeline_mtime = self.model_joblib_path.stat().st_mtime
        self._model_card = card_dict
        self._card_mtime = self.model_card_path.stat().st_mtime

    def load_pipeline(self) -> Any:
        if not self.model_joblib_path.exists():
            raise FileNotFoundError("Model pipeline artifact not found.")

        current_mtime = self.model_joblib_path.stat().st_mtime
        if self._pipeline is None or current_mtime != self._pipeline_mtime:
            self._pipeline = joblib.load(self.model_joblib_path)
            self._pipeline_mtime = current_mtime
        return self._pipeline

    def load_model_card(self) -> Dict[str, Any]:
        if not self.model_card_path.exists():
            raise FileNotFoundError("Model card artifact not found.")

        current_mtime = self.model_card_path.stat().st_mtime
        if self._model_card is None or current_mtime != self._card_mtime:
            self._model_card = json.loads(self.model_card_path.read_text(encoding="utf-8"))
            self._card_mtime = current_mtime
        return self._model_card
