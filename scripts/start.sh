#!/bin/sh
set -eu

# Hosting providers commonly supply PORT. Docker Compose uses 8000 by default.
exec uvicorn backend.production:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --proxy-headers \
  --forwarded-allow-ips="*"
