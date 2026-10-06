from fastapi import APIRouter, Depends
from src.api.schemas import ModelCard
from src.core.dependencies import get_model_repository
from src.infra.abstractions.model_repository import ModelRepository
from src.core.errors import ModelUnavailableError

router = APIRouter(prefix="/v1/model", tags=["model"])

@router.get("", response_model=ModelCard)
async def get_model_card(model_repo: ModelRepository = Depends(get_model_repository)):
    if not model_repo.is_available():
        raise ModelUnavailableError("Le modèle n'est pas disponible.")
    return ModelCard(**model_repo.load_model_card())
