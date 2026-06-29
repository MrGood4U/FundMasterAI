#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$DIR/app.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "No app.pid found — process may not be running or was not started via start.sh"
    exit 1
fi

PID=$(cat "$PID_FILE")
if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    rm -f "$PID_FILE"
    echo "PID $PID stopped"
else
    echo "PID $PID not alive, removing stale pid file"
    rm -f "$PID_FILE"
fi
