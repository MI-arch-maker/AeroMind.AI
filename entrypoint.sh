#!/bin/sh
set -eu
mkdir -p data logs
alembic upgrade head
exec uvicorn web.app:app --host 0.0.0.0 --port "${PORT:-10000}" --proxy-headers --forwarded-allow-ips="*"
