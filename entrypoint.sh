#!/bin/bash
set -e

# 환경변수 기본값 설정
export PORT=${PORT:-8000}
export WEB_CONCURRENCY=${WEB_CONCURRENCY:-2}

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Starting server on port: $PORT with $WEB_CONCURRENCY workers"
exec "$@"
