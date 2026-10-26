from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from src.domain.entities import ModelEntity


class ModelRepository(ABC):
    @abstractmethod
    def save(self, pipeline: Any, model_card: ModelEntity | Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def load_pipeline(self) -> Any:
        pass

    @abstractmethod
    def load_model_card(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass
