#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
PORT="${AGENT_HTTP_PORT:-5003}"

if [ -f app.pid ] && kill -0 "$(cat app.pid)" 2>/dev/null; then
  echo "agent backend already running on port ${PORT}, pid $(cat app.pid)"
  exit 0
fi

PYTHONPATH=src nohup "${PYTHON:-python3}" app.py > app.log 2>&1 &
echo $! > app.pid
echo "agent backend started on port ${PORT}, pid $(cat app.pid)"
