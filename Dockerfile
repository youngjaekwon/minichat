FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    DJANGO_ENV_FILE=env.production

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 의존성 설치 (캐싱 최적화)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv,id=uv-cache \
    uv sync --frozen --no-install-project --group prod

# 프로젝트 복사 및 설치
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv,id=uv-cache \
    uv sync --frozen --group prod

# 정적 파일 수집
RUN uv run python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["sh", "-c", "uv run python manage.py migrate && uv run gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT"]
