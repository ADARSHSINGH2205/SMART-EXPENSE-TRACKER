# syntax=docker/dockerfile:1

# Build the React application with a same-origin API by default. Override the
# build argument only when intentionally hosting the API at another URL.
FROM node:22-alpine AS frontend-build

WORKDIR /frontend

COPY frontend/package.json ./
RUN npm install --no-audit --no-fund

COPY frontend/ ./

ARG VITE_API_URL=/api
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build


# Keep the API and the compiled React app in one image. This avoids a CORS
# dependency in production and is especially suitable for private finance data.
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PAYARC_DATABASE_URL=sqlite:////data/payarc.db

WORKDIR /app

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY backend/ /app/backend/
COPY scripts/start.sh /app/start.sh
COPY --from=frontend-build /frontend/dist/ /app/frontend-dist/

RUN addgroup --system payarc \
    && adduser --system --ingroup payarc --home /app payarc \
    && mkdir -p /data \
    && chown -R payarc:payarc /app /data \
    && chmod +x /app/start.sh

USER payarc

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).read()" || exit 1

CMD ["/app/start.sh"]
