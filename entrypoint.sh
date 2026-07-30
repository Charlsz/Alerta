#!/bin/sh
set -eu

cd /app

# Prefer the small serving DB on Spaces/Docker (override with ALERTA_DUCKDB_PATH).
export ALERTA_DUCKDB_PATH="${ALERTA_DUCKDB_PATH:-data/alerta_serving.duckdb}"

# Download serving DB if missing and ALERTA_DUCKDB_URL is set.
python - <<'PY'
from src.api.live_refresh import bootstrap_duckdb, resolve_duckdb_path
resolve_duckdb_path()
bootstrap_duckdb()
print("bootstrap ok:", __import__("config").config.duckdb_path)
PY

# Hugging Face Spaces exposes $PORT (usually 7860). Next.js proxies /api → API on 8000.
API_PORT="${API_PORT:-8000}"
if [ -n "${SPACE_ID:-}" ]; then
  # Spaces health-check expects the public web process on $PORT / app_port (7860).
  WEB_PORT="${PORT:-7860}"
else
  WEB_PORT="${PORT:-${WEB_PORT:-3000}}"
fi

echo "starting API :${API_PORT}  web :${WEB_PORT} (SPACE_ID=${SPACE_ID:-none})"

uvicorn src.api.main:app --host 0.0.0.0 --port "$API_PORT" &
API_PID=$!

# Wait until API answers before starting the web UI.
i=0
until curl -sf "http://127.0.0.1:${API_PORT}/api/status" >/dev/null 2>&1; do
  i=$((i + 1))
  if [ "$i" -gt 90 ]; then
    echo "API did not become ready in time" >&2
    kill "$API_PID" 2>/dev/null || true
    exit 1
  fi
  sleep 1
done

cd /app/src/web/.next/standalone
PORT="$WEB_PORT" HOSTNAME=0.0.0.0 node server.js &
WEB_PID=$!

trap 'kill $API_PID $WEB_PID 2>/dev/null || true' INT TERM
wait
