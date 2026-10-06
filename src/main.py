from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from src.core.config import settings
from src.core.errors import NotFoundError, InvalidInputError, ModelUnavailableError
from src.api.error_handlers import (
    validation_exception_handler,
    not_found_handler,
    invalid_input_handler,
    model_unavailable_handler,
    global_exception_handler
)

from src.api.routers import health, orders, predictions, model

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="API de prédiction d'éligibilité à la livraison express"
)

# Enregistrement des gestionnaires d'erreurs
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(NotFoundError, not_found_handler)
app.add_exception_handler(InvalidInputError, invalid_input_handler)
app.add_exception_handler(ModelUnavailableError, model_unavailable_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Enregistrement des routeurs
app.include_router(health.router)
app.include_router(orders.router)
app.include_router(predictions.router)
app.include_router(model.router)
