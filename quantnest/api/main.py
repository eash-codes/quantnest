"""QuantNest FastAPI application factory."""

from __future__ import annotations

import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from quantnest.api.errors import register_exception_handlers
from quantnest.infra.db.session import init_db
from quantnest.infra.logging import configure_logging, request_id_var

from .auth import router as auth_router
from .history import router as history_router
from .market import router as market_router
from .orders import router as orders_router
from .portfolio import router as portfolio_router

logger = logging.getLogger(__name__)


def _allowed_origins() -> list[str]:
    """CORS origins from ``CORS_ORIGINS`` (comma-separated)."""
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    logger.info(
        "QuantNest API starting",
        extra={"market_provider": os.getenv("QUANTNEST_MARKET_PROVIDER", "yfinance")},
    )
    init_db()
    yield
    logger.info("QuantNest API shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="QuantNest Trading Platform",
        version="11.3.0",
        description="A trading simulator built with domain-driven design.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Transaction-ID"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        """Assign a correlation ID and log the outcome of every request."""
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_var.set(request_id)
        started = time.perf_counter()

        try:
            response = await call_next(request)

            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            response.headers["X-Request-ID"] = request_id

            # Logged before the context var is reset, so the correlation ID
            # is present on the completion record too.
            logger.info(
                "Request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
            return response
        except Exception:
            # The exception handlers build the response; just record the timing.
            logger.exception(
                "Request failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            raise
        finally:
            request_id_var.reset(token)

    register_exception_handlers(app)

    app.include_router(auth_router)
    app.include_router(portfolio_router)
    app.include_router(history_router)
    app.include_router(orders_router)
    app.include_router(market_router)

    @app.get("/", tags=["meta"], summary="Service metadata")
    async def root() -> dict:
        return {
            "service": "QuantNest Trading Platform",
            "version": app.version,
            "docs": "/docs",
        }

    @app.get("/health", tags=["meta"], summary="Liveness probe")
    async def health() -> dict:
        return {"status": "healthy", "version": app.version}

    return app


app = create_app()
