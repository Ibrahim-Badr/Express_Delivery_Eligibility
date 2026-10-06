from fastapi import APIRouter, Depends, Response
from src.api.schemas import HealthStatus, ReadinessStatus
from src.core.config import settings
from src.core.dependencies import get_model_repository
from src.infra.abstractions.model_repository import ModelRepository

router = APIRouter(tags=["health"])

@router.get(//health/, response_model=HealthStatus)
async def get_health():
    return HealthStatus(status="ok", service=settings.app_name, version="1.0.0")

@router.get(//health/ready/, response_model=ReadinessStatus)
async def get_readiness(response: Response, model_repo: ModelRepository = Depends(get_model_repository)):
    if model_repo.is_available():
        return ReadinessStatus(
            status="ready",
            checks={"model": "loaded"},
            version="1.0.0"
        )
    else:
        response.status_code = 503
        return ReadinessStatus(
            status="not_ready",
            checks={"model": "unavailable"},
            version="1.0.0"
        )
