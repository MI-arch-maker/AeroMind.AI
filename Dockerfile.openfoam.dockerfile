FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM openfoam/openfoam11-paraview510
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV AEROMIND_OPENFOAM=1 PORT=10000 DATA_DIR=/var/data
COPY requirements.txt ./
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt
COPY backend/ ./backend/
COPY --from=web /web/dist ./static/
EXPOSE 10000
CMD ["python3", "-m", "backend.app.main"]