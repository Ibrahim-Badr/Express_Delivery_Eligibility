from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from src.core.errors import NotFoundError, InvalidInputError, ModelUnavailableError
from src.api.schemas import ErrorResponse

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="validation_error",
            message="Données invalides",
            details=[str(e) for e in exc.errors()]
        ).model_dump()
    )

async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(
            error="not_found",
            message=exc.message
        ).model_dump()
    )

async def invalid_input_handler(request: Request, exc: InvalidInputError):
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="invalid_input",
            message=exc.message
        ).model_dump()
    )

async def model_unavailable_handler(request: Request, exc: ModelUnavailableError):
    return JSONResponse(
        status_code=503,
        content=ErrorResponse(
            error="model_unavailable",
            message=exc.message
        ).model_dump()
    )

async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="internal_error",
            message="Une erreur interne est survenue"
        ).model_dump()
    )
