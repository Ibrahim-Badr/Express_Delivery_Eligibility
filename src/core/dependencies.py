import os

from src.infra.abstractions.model_repository import ModelRepository
from src.infra.abstractions.order_repository import OrderRepository
from src.infra.abstractions.order_store import OrderStore
from src.infra.abstractions.prediction_store import PredictionStore
from src.infra.local.file_model_repository import FileModelRepository

_model_repository: ModelRepository = FileModelRepository()

# Instantiate order store according to configuration
if os.getenv("DATABASE_URL") and "postgresql" in os.getenv("DATABASE_URL", ""):
    from src.infra.database.postgres_order_repository import PostgresOrderRepository
    from src.infra.database.postgres_prediction_store import PostgresPredictionStore

    _order_store: OrderRepository = PostgresOrderRepository()
    _prediction_store: PredictionStore = PostgresPredictionStore()
else:
    from src.infra.local.memory_order_store import MemoryOrderStore
    from src.infra.local.memory_prediction_store import MemoryPredictionStore

    _order_store = MemoryOrderStore()
    _prediction_store = MemoryPredictionStore()


def get_order_store() -> OrderStore:
    return _order_store


def get_order_repository() -> OrderRepository:
    return _order_store


def get_model_repository() -> ModelRepository:
    return _model_repository


def get_prediction_store() -> PredictionStore:
    return _prediction_store
