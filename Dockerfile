# Imagen única para la demo en la nube: API FastAPI (interna, puerto 8000)
# + interfaz Next.js (pública, puerto $PORT). Usada por render.yaml.
#
#   docker build -t mercacircular .
#   docker run --rm -p 10000:10000 mercacircular   → http://localhost:10000

# ── 1. Compilar el frontend ─────────────────────────────────────────────────
FROM node:22-bookworm-slim AS web
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
ENV NEXT_TELEMETRY_DISABLED=1 \
    NEXT_OUTPUT=standalone \
    BACKEND_URL=http://127.0.0.1:8000
RUN npm run build

# ── 2. Imagen final: Python + el binario de Node ────────────────────────────
FROM python:3.12-slim-bookworm
RUN apt-get update \
 && apt-get install -y --no-install-recommends libstdc++6 \
 && rm -rf /var/lib/apt/lists/*
COPY --from=web /usr/local/bin/node /usr/local/bin/node

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NEXT_TELEMETRY_DISABLED=1 \
    SEED_DEMO_DATA=true \
    ALLOW_DEMO_RESET=true \
    PORT=10000

WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY backend/app backend/app
COPY backend/models backend/models
COPY demo-data demo-data
COPY --from=web /app/frontend/.next/standalone frontend/
COPY --from=web /app/frontend/.next/static frontend/.next/static
COPY --from=web /app/frontend/public frontend/public
COPY docker/start.sh /app/start.sh

RUN chmod +x /app/start.sh \
 && mkdir -p /app/database \
 && useradd --create-home --uid 10001 app \
 && chown -R app /app
USER app

EXPOSE 10000
CMD ["/app/start.sh"]
