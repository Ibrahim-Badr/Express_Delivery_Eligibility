from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse

from src.api.error_handlers import (
    global_exception_handler,
    invalid_input_handler,
    model_unavailable_handler,
    not_found_handler,
    validation_exception_handler,
)
from src.api.routers import health, model, orders, predictions
from src.api.schemas import OrderFeatures, Prediction
from src.core.config import settings
from src.core.dependencies import get_model_repository, get_prediction_store
from src.core.errors import InvalidInputError, ModelUnavailableError, NotFoundError
from src.infra.abstractions.model_repository import ModelRepository
from src.infra.abstractions.prediction_store import PredictionStore

app = FastAPI(
    title=settings.app_name,
    version=settings.model_version,
    description="Express Delivery Eligibility Prediction REST API",
)

# Register custom exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(NotFoundError, not_found_handler)
app.add_exception_handler(InvalidInputError, invalid_input_handler)
app.add_exception_handler(ModelUnavailableError, model_unavailable_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Register API routers
app.include_router(health.router)
app.include_router(orders.router)
app.include_router(predictions.router)
app.include_router(model.router)


@app.get("/", include_in_schema=False)
async def root_redirect():
    """Redirect root URL to interactive Swagger UI documentation."""
    return RedirectResponse(url="/docs")


@app.post("/predict", response_model=Prediction, tags=["predictions"])
async def predict_root_alias(
    order: OrderFeatures,
    model_repo: ModelRepository = Depends(get_model_repository),
    pred_store: PredictionStore = Depends(get_prediction_store),
):
    """Root alias for POST /v1/predictions."""
    return await predictions.create_prediction(
        order=order,
        model_repo=model_repo,
        pred_store=pred_store,
    )
