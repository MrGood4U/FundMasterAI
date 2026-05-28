#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Stopping all backends ==="

for svc in market_backend news_backend portfolio_backend; do
    echo -n "[$svc] "
    bash "$DIR/$svc/stop.sh"
done

echo "=== Done ==="
