from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class ApiError(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] = Field(default_factory=list)
    request_id: str | None = None


class DomainError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, details: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        body = ApiError(code=exc.code, message=exc.message, details=exc.details, request_id=getattr(request.state, "request_id", None))
        return JSONResponse(status_code=exc.status_code, content=body.model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [{"location": list(error.get("loc", [])), "message": error.get("msg", "invalid value")} for error in exc.errors()]
        body = ApiError(code="VALIDATION_ERROR", message="Ошибка валидации запроса", details=details, request_id=getattr(request.state, "request_id", None))
        return JSONResponse(status_code=422, content=body.model_dump())
