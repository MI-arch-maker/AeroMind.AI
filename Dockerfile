FROM node:22-bookworm-slim AS frontend-builder
WORKDIR /frontend
RUN npm install --global pnpm@10.18.0
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend ./
RUN pnpm exec vite build --config vite.config.ts

FROM nginx:1.27-alpine AS frontend-runtime
COPY --from=frontend-builder /frontend/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

FROM python:3.11-slim AS backend-runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PYTHONPATH=/app
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
