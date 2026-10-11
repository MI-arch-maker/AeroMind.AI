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
RUN mkdir -p /app/data /app/logs && chown -R appuser:appuser /app
RUN chmod 0555 /app/entrypoint.sh
USER appuser

ENV PORT=10000
EXPOSE 10000

CMD ["/app/entrypoint.sh"]
