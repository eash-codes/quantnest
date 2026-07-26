"""Development entrypoint: run the QuantNest API with uvicorn."""

from __future__ import annotations

import os

import uvicorn

from quantnest.infra.logging import configure_logging


def main() -> None:
    configure_logging()
    uvicorn.run(
        "quantnest.api.main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "true").lower() in {"1", "true", "yes"},
        log_config=None,
    )


if __name__ == "__main__":
    main()
