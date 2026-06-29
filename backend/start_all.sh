#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Starting all backends ==="

for svc in market_backend news_backend portfolio_backend; do
    echo -n "[$svc] "
    bash "$DIR/$svc/start.sh"
done

echo "=== Done ==="
