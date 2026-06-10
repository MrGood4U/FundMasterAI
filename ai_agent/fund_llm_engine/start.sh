#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

HOST="${AGENT_HTTP_HOST:-127.0.0.1}"
PORT="${AGENT_HTTP_PORT:-5003}"
PID_FILE="$DIR/app.pid"
LOG_FILE="$DIR/app.log"
HEALTH_URL="http://${HOST}:${PORT}/health"

if [ -n "${PYTHON:-}" ]; then
  PYTHON_BIN="$PYTHON"
elif [ -x "$DIR/.venv/bin/python" ]; then
  PYTHON_BIN="$DIR/.venv/bin/python"
else
  PYTHON_BIN="python3.11"
fi

export AGENT_HTTP_HOST="$HOST"
export AGENT_HTTP_PORT="$PORT"
export AGENT_DEBUG="${AGENT_DEBUG:-false}"
export AGENT_RELOAD="${AGENT_RELOAD:-false}"
export PYTHONPATH="$DIR/src${PYTHONPATH:+:$PYTHONPATH}"

health_ok() {
  curl -fsS --max-time 2 "$HEALTH_URL" >/dev/null 2>&1
}

url_ok() {
  curl -fsS --max-time 2 "$1" >/dev/null 2>&1
}

wait_for_health() {
  local attempts="${1:-10}"
  for _ in $(seq 1 "$attempts"); do
    if health_ok; then
      return 0
    fi
    sleep 0.5
  done
  return 1
}

if [ -z "${NEWS_BACKEND_URL:-}" ]; then
  if url_ok "http://127.0.0.1:5000/api/news/functions?tag=fund"; then
    export NEWS_BACKEND_URL="http://127.0.0.1:5000"
  elif url_ok "http://127.0.0.1:5010/api/news/functions?tag=fund"; then
    export NEWS_BACKEND_URL="http://127.0.0.1:5010"
  else
    export NEWS_BACKEND_URL="http://127.0.0.1:5000"
  fi
else
  export NEWS_BACKEND_URL
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python executable not found: $PYTHON_BIN"
  echo "Set PYTHON=/path/to/python or create .venv in $DIR"
  exit 1
fi

if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    if wait_for_health 6; then
      echo "agent backend already running at $HEALTH_URL, pid $PID"
      exit 0
    fi
    echo "agent backend pid $PID is alive, but health check failed: $HEALTH_URL"
    echo "see log: $LOG_FILE"
    exit 1
  fi
  echo "removing stale pid file: $PID_FILE"
  rm -f "$PID_FILE"
fi

if wait_for_health 6; then
  echo "agent backend already responds at $HEALTH_URL"
  echo "no app.pid found; it may have been started outside start.sh"
  exit 0
fi

if command -v lsof >/dev/null 2>&1 && lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "port $PORT is already in use, but health check failed: $HEALTH_URL"
  lsof -iTCP:"$PORT" -sTCP:LISTEN || true
  exit 1
fi

touch "$LOG_FILE"
echo "starting agent backend at $HEALTH_URL"
echo "python: $PYTHON_BIN"
echo "log: $LOG_FILE"
echo "news backend: $NEWS_BACKEND_URL"

PID="$("$PYTHON_BIN" -c 'import os
import subprocess
import sys

log_path, app_path, python_bin = sys.argv[1:4]
log_file = open(log_path, "ab", buffering=0)
process = subprocess.Popen(
    [python_bin, app_path],
    cwd=os.path.dirname(app_path),
    stdin=subprocess.DEVNULL,
    stdout=log_file,
    stderr=subprocess.STDOUT,
    env=os.environ.copy(),
    start_new_session=True,
)
print(process.pid)
' "$LOG_FILE" "$DIR/app.py" "$PYTHON_BIN")"
echo "$PID" > "$PID_FILE"

for _ in $(seq 1 20); do
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "agent backend failed to start; see log: $LOG_FILE"
    rm -f "$PID_FILE"
    tail -n 40 "$LOG_FILE" || true
    exit 1
  fi
  if health_ok; then
    echo "agent backend started at $HEALTH_URL, pid $PID"
    exit 0
  fi
  sleep 0.5
done

echo "agent backend pid $PID started, but health check did not pass: $HEALTH_URL"
echo "see log: $LOG_FILE"
tail -n 40 "$LOG_FILE" || true
exit 1
