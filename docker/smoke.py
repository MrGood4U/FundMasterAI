#!/usr/bin/env python3
"""End-to-end smoke test for the containerized FundMasterAI stack."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


BASE_URL = os.getenv("SMOKE_BASE_URL", "http://frontend").rstrip("/")
FUND_CODE = os.getenv("SMOKE_FUND_CODE", "000001").strip() or "000001"
TIMEOUT = int(os.getenv("SMOKE_TIMEOUT_SECONDS", "300"))

FRONTEND_PAGES = (
    ("/portfolio-overview.html", b"Portfolio Overview"),
    ("/equity-funds.html", b"Equity Funds"),
    ("/debt-funds.html", b"Debt Portfolio"),
    ("/global-investment.html", b"Global Strategic Matrix"),
    ("/fund-deep-dive.html", b"Fund Deep Dive"),
    ("/market-hub.html", b"Market Hub"),
    ("/market-flow.html", b"Market Liquidity"),
    ("/index.html", b"Market Intelligence"),
    ("/ai-insights.html", b"AI Fund Analysis"),
    ("/settings.html", b"Settings"),
)


def fetch(path: str, *, payload: dict | None = None):
    data = None
    headers = {}
    method = "GET"
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
        method = "POST"

    request = urllib.request.Request(
        f"{BASE_URL}{path}", data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            body = response.read()
            return response.status, body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} returned HTTP {exc.code}: {body[:500]}") from exc


def fetch_json(path: str, *, payload: dict | None = None) -> dict:
    status, body = fetch(path, payload=payload)
    if status != 200:
        raise RuntimeError(f"{path} returned HTTP {status}")
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{path} did not return JSON: {body[:200]!r}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(f"{path} returned {type(parsed).__name__}, expected object")
    return parsed


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    for path, marker in FRONTEND_PAGES:
        status, page = fetch(path)
        require(
            status == 200 and marker in page,
            f"frontend page {path} is not available",
        )
    print(f"[ok] frontend: {len(FRONTEND_PAGES)} primary pages")

    for path, label in (
        ("/api/market/functions?tag=fund", "market registry"),
        ("/api/news/functions?tag=fund", "news registry"),
        ("/api/portfolio/functions", "portfolio registry"),
        ("/api/ai/functions", "agent registry"),
        ("/api/ai/llm/models", "agent model catalog"),
    ):
        body = fetch_json(path)
        require(bool(body), f"{label} returned an empty object")
        print(f"[ok] {label}")

    result = fetch_json(
        "/api/ai/fund/analyze",
        payload={
            "code": FUND_CODE,
            "start_date": "2025/01/01",
            "mock": True,
            "max_nav_points": 80,
            "max_news_items": 1,
            "top_holdings_n": 5,
            "max_parallel_agents": 2,
        },
    )
    require(result.get("code") == 200, f"analysis code is {result.get('code')!r}")
    coverage = result.get("coverage") or {}
    data = result.get("data") or {}
    metadata = data.get("metadata") or {}
    outputs = data.get("agent_outputs") or []
    require(int(coverage.get("nav_points") or 0) > 0, "analysis returned no NAV data")
    require(metadata.get("llm_mode") == "mock", "analysis did not use mock LLM mode")
    require(len(outputs) >= 3, "analysis returned fewer than three Agent outputs")
    print(
        f"[ok] fund {FUND_CODE}: {coverage['nav_points']} NAV points, "
        f"{len(outputs)} Agent outputs, mock LLM"
    )
    print("FundMasterAI Docker smoke test passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[failed] {exc}", file=sys.stderr)
        raise SystemExit(1)
