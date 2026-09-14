# Backend API image — multi-stage build (matches infra/docker/backend.prod.Dockerfile strategy).
# Build: docker build -f backend/Dockerfile backend/
ARG PYTHON_VERSION=3.13-slim-bookworm

# --- builder: compile C extensions ---
FROM python:${PYTHON_VERSION} AS builder
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt ./
RUN pip install --prefix=/install -r requirements.txt

# --- runtime: minimal final image ---
FROM python:${PYTHON_VERSION} AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code
COPY --from=builder /install /usr/local
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
