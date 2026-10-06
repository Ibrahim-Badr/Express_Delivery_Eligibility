from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class OrderStore(ABC):
    @abstractmethod
    def save(self, order_id: str, order_data: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def get(self, order_id: str) -> Optional[Dict[str, Any]]:
        pass
