# Production backend image: multi-stage, non-root, minimal attack surface.
# Build from repo root: docker build -f infra/docker/backend.prod.Dockerfile .

# ---------------------------------------------------------------------------
# Stage 1: builder — compile C extensions (psycopg, bcrypt) then discard.
# ---------------------------------------------------------------------------
ARG PYTHON_VERSION=3.13-slim-bookworm

FROM python:${PYTHON_VERSION} AS builder
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY backend/requirements.txt ./
RUN pip install --prefix=/install -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2: runtime — only what is needed to run the app.
# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION} AS runtime

# Install only the minimal shared library the PostgreSQL client needs.
# build-essential, gcc, make, perl, pcre2 etc. are NOT installed here.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libpq5 \
       curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 10001 appuser

WORKDIR /code

# Copy pre-built Python packages from builder (no compilers in final image).
COPY --from=builder /install /usr/local

# Application code.
COPY backend/app ./app
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./
COPY infra/docker/entrypoint.sh ./entrypoint.sh

RUN chmod +x entrypoint.sh \
    && chown -R appuser:appuser /code

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

ENTRYPOINT ["./entrypoint.sh"]
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", "--workers", "4", "--graceful-timeout", "30"]
