FROM node:22-bookworm-slim AS frontend-builder
WORKDIR /frontend

RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend ./
RUN pnpm exec vite build --config vite.config.ts

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app
RUN useradd --create-home --uid 10001 appuser

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
COPY --from=frontend-builder /frontend/dist /app/frontend/dist

RUN mkdir -p /app/data /app/logs && chmod 0555 /app/entrypoint.sh && chown -R appuser:appuser /app
USER appuser

ENV PORT=10000
EXPOSE 10000
CMD ["/app/entrypoint.sh"]
