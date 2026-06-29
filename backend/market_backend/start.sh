#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
nohup python3.11 app.py >> "$DIR/app.log" 2>&1 &
PID=$!
echo $PID > "$DIR/app.pid"
echo "PID $PID started — $DIR/app.log"
