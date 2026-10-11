# ---- Frontend ----
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- Runtime ----
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PORT=10000 DATA_DIR=/var/data
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY --from=web /web/dist ./static/
EXPOSE 10000
CMD ["python", "-m", "backend.app.main"]