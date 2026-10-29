from src.core.config import settings
from src.infra.abstractions.model_repository import ModelRepository
from src.infra.abstractions.order_repository import OrderRepository
from src.infra.abstractions.prediction_store import PredictionStore
from src.infra.local.file_model_repository import FileModelRepository

_model_repository: ModelRepository = FileModelRepository()

if "postgresql" in settings.database_url:
    from src.infra.database.postgres_order_repository import PostgresOrderRepository
    from src.infra.database.postgres_prediction_store import PostgresPredictionStore

    _order_repository: OrderRepository = PostgresOrderRepository()
    _prediction_store: PredictionStore = PostgresPredictionStore()
else:
    from src.infra.local.memory_order_store import MemoryOrderStore
    from src.infra.local.memory_prediction_store import MemoryPredictionStore

    _order_repository = MemoryOrderStore()
    _prediction_store = MemoryPredictionStore()


def get_order_repository() -> OrderRepository:
    return _order_repository


# Backward-compatible dependency alias
get_order_store = get_order_repository


def get_model_repository() -> ModelRepository:
    return _model_repository


def get_prediction_store() -> PredictionStore:
    return _prediction_store
