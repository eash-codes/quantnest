# ── Stage 1: build wheels ────────────────────────────────────────────────
# Compiling in a throwaway stage keeps build tooling out of the final image.
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY quantnest ./quantnest

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip \
    && pip install .


# ── Stage 2: runtime ─────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    DATABASE_URL="sqlite:////data/quantnest.db" \
    LOG_FORMAT=json \
    ENVIRONMENT=production

# curl is needed for the container healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Run as an unprivileged user; a container that never needs root should not have it.
RUN useradd --create-home --uid 10001 quantnest

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=quantnest:quantnest quantnest ./quantnest
COPY --chown=quantnest:quantnest scripts ./scripts

# Named volume mount point for the SQLite file, so data survives a rebuild.
RUN mkdir -p /data && chown quantnest:quantnest /data
VOLUME ["/data"]

USER quantnest

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail --silent http://localhost:8000/health || exit 1

CMD ["uvicorn", "quantnest.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
