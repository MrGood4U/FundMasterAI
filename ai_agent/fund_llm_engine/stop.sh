#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f app.pid ]; then
  echo "agent backend is not running"
  exit 0
fi

PID="$(cat app.pid)"
if kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  echo "agent backend stopped, pid ${PID}"
else
  echo "agent backend pid ${PID} is not running"
fi
rm -f app.pid
