#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

HOST="${AGENT_HTTP_HOST:-127.0.0.1}"
PORT="${AGENT_HTTP_PORT:-5003}"
PID_FILE="$DIR/app.pid"
HEALTH_URL="http://${HOST}:${PORT}/health"

health_ok() {
  curl -fsS --max-time 2 "$HEALTH_URL" >/dev/null 2>&1
}

stop_pid() {
  local pid="$1"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid"
    echo "stopped pid $pid"
  fi
}

if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    stop_pid "$PID"
  else
    echo "agent backend pid ${PID:-unknown} is not running"
  fi
  rm -f "$PID_FILE"
else
  echo "no app.pid found"
fi

sleep 1

if command -v lsof >/dev/null 2>&1; then
  PIDS="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN || true)"
  if [ -n "$PIDS" ]; then
    echo "stopping listener(s) on port $PORT"
    for pid in $PIDS; do
      stop_pid "$pid"
    done
    sleep 1
  fi
fi

if health_ok; then
  echo "agent backend still responds at $HEALTH_URL"
  exit 1
fi

echo "agent backend stopped"
