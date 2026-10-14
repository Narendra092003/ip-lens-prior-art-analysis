#!/usr/bin/env bash
set -Eeuo pipefail

cd /app

uv run python scripts/seed_demo_corpus.py

if [[ "${DEMO_MODE:-false}" == "true" ]]; then
  export MAX_CLAIMS=4
  export MAX_UPLOAD_MB=2
fi

uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8001 &
api_pid=$!
ui_pid=""

cleanup() {
  if [[ -n "$ui_pid" ]] && kill -0 "$ui_pid" 2>/dev/null; then
    kill "$ui_pid" 2>/dev/null || true
  fi
  if kill -0 "$api_pid" 2>/dev/null; then
    kill "$api_pid" 2>/dev/null || true
  fi
  wait "$api_pid" 2>/dev/null || true
  if [[ -n "$ui_pid" ]]; then
    wait "$ui_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

healthy=false
for _ in $(seq 1 60); do
  if ! kill -0 "$api_pid" 2>/dev/null; then
    echo "API process exited before becoming healthy." >&2
    exit 1
  fi
  if uv run python -c \
    "from urllib.request import urlopen; urlopen('http://127.0.0.1:8001/health', timeout=2).read()" \
    >/dev/null 2>&1; then
    healthy=true
    break
  fi
  sleep 1
done

if [[ "$healthy" != "true" ]]; then
  echo "API did not become healthy on port 8001." >&2
  exit 1
fi

API_BASE_URL=http://127.0.0.1:8001 \
  uv run streamlit run frontend/streamlit_app.py \
    --server.headless true --server.address 0.0.0.0 --server.port 7860 &
ui_pid=$!

set +e
wait -n "$api_pid" "$ui_pid"
exit_code=$?
set -e
exit "$exit_code"
