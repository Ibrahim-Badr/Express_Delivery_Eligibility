from src.infra.abstractions.order_store import OrderStore
from src.infra.abstractions.model_repository import ModelRepository
from src.infra.local.memory_order_store import MemoryOrderStore
from src.infra.local.file_model_repository import FileModelRepository

# Instances uniques des adaptateurs en mémoire
_order_store = MemoryOrderStore()
_model_repository = FileModelRepository()

def get_order_store() -> OrderStore:
    return _order_store

def get_model_repository() -> ModelRepository:
    return _model_repository
