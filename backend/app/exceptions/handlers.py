from fastapi import Request
from fastapi.responses import JSONResponse

from app.exceptions.base import AppError


def error_to_content(exc: AppError, path: str) -> dict:
    payload = {
        "detail": exc.message,
        "error_code": exc.error_code,
        "path": path,
    }
    if exc.details:
        payload["details"] = exc.details
    return payload


async def app_exception_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_to_content(exc, request.url.path),
    )
