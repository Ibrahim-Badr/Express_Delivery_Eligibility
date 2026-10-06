from abc import ABC, abstractmethod
from typing import Dict, Any

class ModelRepository(ABC):
    @abstractmethod
    def load_pipeline(self) -> Any:
        pass

    @abstractmethod
    def load_model_card(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass
