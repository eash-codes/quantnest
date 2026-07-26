"""Centralised exception handling.

Every error leaves the API as an RFC 9457 ``application/problem+json`` body.
Domain exceptions map to meaningful status codes; anything unexpected is logged
in full server-side and returned to the client as a generic 500, so a Python
traceback can never leak.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from quantnest.domain.exceptions import (
    DomainError,
    InsufficientFundsError,
    InsufficientPositionsError,
    OrderExecutionError,
    OrderNotFoundError,
    OrderStateError,
    UnknownSymbolError,
    ValidationError as DomainValidationError,
)
from quantnest.infra.logging import request_id_var

logger = logging.getLogger(__name__)

PROBLEM_JSON = "application/problem+json"

#: Domain exception -> (HTTP status, human-readable title)
_DOMAIN_STATUS_MAP: dict[type[DomainError], tuple[int, str]] = {
    DomainValidationError: (status.HTTP_400_BAD_REQUEST, "Invalid request"),
    UnknownSymbolError: (status.HTTP_404_NOT_FOUND, "Unknown symbol"),
    OrderNotFoundError: (status.HTTP_404_NOT_FOUND, "Order not found"),
    InsufficientFundsError: (status.HTTP_409_CONFLICT, "Insufficient funds"),
    InsufficientPositionsError: (status.HTTP_409_CONFLICT, "Insufficient holdings"),
    OrderStateError: (status.HTTP_409_CONFLICT, "Invalid order state"),
    OrderExecutionError: (status.HTTP_422_UNPROCESSABLE_CONTENT, "Order could not be executed"),
}


def _problem(
    request: Request,
    *,
    status_code: int,
    title: str,
    detail: str | None = None,
    error_type: str = "about:blank",
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        media_type=PROBLEM_JSON,
        content={
            "type": error_type,
            "title": title,
            "status": status_code,
            "detail": detail,
            "instance": str(request.url.path),
            "request_id": request_id_var.get(),
        },
    )


def _resolve_domain_error(exc: DomainError) -> tuple[int, str]:
    for exc_type, mapping in _DOMAIN_STATUS_MAP.items():
        if isinstance(exc, exc_type):
            return mapping
    return status.HTTP_400_BAD_REQUEST, "Request rejected"


def register_exception_handlers(app: FastAPI) -> None:
    """Attach every handler to the application."""

    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        status_code, title = _resolve_domain_error(exc)

        logger.info(
            "Domain rule rejected the request",
            extra={
                "error_code": exc.code,
                "error_type": type(exc).__name__,
                "path": request.url.path,
                "status_code": status_code,
            },
        )

        return _problem(
            request,
            status_code=status_code,
            title=title,
            detail=str(exc),
            error_type=exc.code,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        messages = []
        for error in exc.errors():
            location = ".".join(str(part) for part in error.get("loc", []) if part != "body")
            message = error.get("msg", "invalid value")
            messages.append(f"{location}: {message}" if location else message)

        detail = "; ".join(messages) or "The request payload is invalid."

        logger.info(
            "Request failed validation",
            extra={"path": request.url.path, "errors": messages},
        )

        return _problem(
            request,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            title="Validation error",
            detail=detail,
            error_type="validation_error",
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        title = {
            400: "Bad request",
            401: "Unauthorised",
            403: "Forbidden",
            404: "Not found",
            405: "Method not allowed",
            409: "Conflict",
            429: "Too many requests",
        }.get(exc.status_code, "Request failed")

        return _problem(
            request,
            status_code=exc.status_code,
            title=title,
            detail=str(exc.detail) if exc.detail else None,
            error_type="http_error",
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Full detail goes to the logs; the client sees nothing internal.
        logger.exception(
            "Unhandled exception while serving request",
            extra={
                "path": request.url.path,
                "method": request.method,
                "error_type": type(exc).__name__,
            },
        )

        return _problem(
            request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            title="Internal server error",
            detail="An unexpected error occurred. Please try again or contact support.",
            error_type="internal_error",
        )
