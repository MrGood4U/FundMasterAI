#!/usr/bin/env python3
"""Preview how the existing portfolio Agent maps into the Overview widget.

This script deliberately does not touch the frontend.  With no arguments it
runs the production portfolio pipeline against deterministic sample data, so
the preview is reproducible without any backend service.  Pass ``--agent-url``
and one or more ``--position CODE=AMOUNT`` arguments to exercise the real HTTP
endpoint once the Market and Agent services are running.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fund_llm.contracts import (  # noqa: E402
    AnalysisWindow,
    FundInfo,
    NavPoint,
    PortfolioAnalysisInput,
    PortfolioFundData,
)
from fund_llm.portfolio_pipeline import run_mock_portfolio_analysis_for_input  # noqa: E402


GENERIC_MOCK_SUMMARIES = {
    "mock portfolio narrative.",
    "mock llm narrative generated for portfolio-level analysis.",
}


def _nav_series(profile: str, points: int = 320) -> list[NavPoint]:
    """Build deterministic sample NAV paths with one shared stress window."""

    start = date(2025, 1, 2)
    nav = 1.0
    rows = [NavPoint(date=start.isoformat(), nav=nav)]
    for index in range(1, points):
        if profile == "core_growth":
            daily_return = 0.0008 + 0.021 * math.sin(index * 1.7)
            if 142 <= index <= 153:
                daily_return = -0.025
        elif profile == "sector_growth":
            daily_return = 0.0010 + 0.026 * math.sin(index * 1.7 + 0.35)
            if 142 <= index <= 153:
                daily_return = -0.022
        else:
            daily_return = 0.0002 + 0.0015 * math.sin(index * 0.65)

        nav = max(0.05, nav * (1.0 + daily_return))
        rows.append(
            NavPoint(
                date=(start + timedelta(days=index)).isoformat(),
                nav=round(nav, 8),
            )
        )
    return rows


def build_sample_input() -> PortfolioAnalysisInput:
    """Return labelled sample data that exercises concentration risk paths."""

    funds = [
        PortfolioFundData(
            fund_info=FundInfo(
                code="000001",
                name="Sample Core Growth Fund",
                asset_type="fund_open",
                category="混合型-偏股",
            ),
            nav_series=_nav_series("core_growth"),
            weight=0.65,
            requested_weight=6500,
            top_holdings=[
                {
                    "stock_code": "DEMO01",
                    "stock_name": "Shared AI Holding (sample)",
                    "net_value_pct": "18.0",
                    "quarter": "sample",
                },
                {
                    "stock_code": "DEMO02",
                    "stock_name": "Core Holding (sample)",
                    "net_value_pct": "12.0",
                    "quarter": "sample",
                },
            ],
            industry_exposure={"Technology": 0.55, "Consumer": 0.25},
            asset_allocation={"stock": 0.90, "bond": 0.03, "cash": 0.07},
        ),
        PortfolioFundData(
            fund_info=FundInfo(
                code="161725",
                name="Sample Sector Growth Fund",
                asset_type="fund_open",
                category="股票型-指数",
            ),
            nav_series=_nav_series("sector_growth"),
            weight=0.25,
            requested_weight=2500,
            top_holdings=[
                {
                    "stock_code": "DEMO01",
                    "stock_name": "Shared AI Holding (sample)",
                    "net_value_pct": "25.0",
                    "quarter": "sample",
                }
            ],
            industry_exposure={"Technology": 0.70, "Consumer": 0.10},
            asset_allocation={"stock": 0.97, "cash": 0.03},
        ),
        PortfolioFundData(
            fund_info=FundInfo(
                code="003358",
                name="Sample Bond Fund",
                asset_type="fund_open",
                category="债券型-普通债券",
            ),
            nav_series=_nav_series("bond"),
            weight=0.10,
            requested_weight=1000,
            asset_allocation={"bond": 0.88, "cash": 0.12},
        ),
    ]
    return PortfolioAnalysisInput(
        request_id="portfolio-widget-preview-sample",
        funds=funds,
        analysis_window=AnalysisWindow(
            start_date=funds[0].nav_series[0].date,
            end_date=funds[0].nav_series[-1].date,
            as_of_date=funds[0].nav_series[-1].date,
        ),
        client_risk_profile="balanced",
        extra_context={
            "data_source": "deterministic_labelled_sample",
            "weights_rescaled": "false",
            "fund_count": str(len(funds)),
        },
    )


def _percentage(value: Any) -> str:
    try:
        return f"{float(value):.2%}"
    except (TypeError, ValueError):
        return "N/A"


def build_widget_preview(data: dict[str, Any]) -> dict[str, Any]:
    """Map the current Agent response into the three Overview UI fields."""

    metrics = data.get("quant_metrics") or {}
    constituents = data.get("constituents") or []
    industry = data.get("industry_lookthrough") or {}
    holdings = data.get("holdings_lookthrough") or {}

    volatility = float(metrics.get("annualized_volatility") or 0.0)
    drawdown = float(metrics.get("max_drawdown") or 0.0)
    largest_weight = max(
        (float(row.get("weight") or 0.0) for row in constituents),
        default=0.0,
    )
    top_sector_weight = float(industry.get("top_sector_weight") or 0.0)
    overlap_count = len(holdings.get("overlapping_holdings") or [])

    severe_flags = [
        drawdown <= -0.30,
        volatility >= 0.40,
        largest_weight >= 0.80,
    ]
    warning_flags = [
        drawdown <= -0.15,
        volatility >= 0.25,
        largest_weight > 0.60,
        top_sector_weight > 0.30,
        overlap_count > 0,
    ]
    warning_count = sum(bool(flag) for flag in warning_flags)
    overall_rating = str(data.get("overall_rating") or "").lower()
    if any(severe_flags) or overall_rating == "avoid" or warning_count >= 2:
        signal = "RED"
        signal_detail = "high portfolio risk"
    elif warning_count or overall_rating in {"watch", "hold"}:
        signal = "YELLOW"
        signal_detail = "elevated or concentrated risk"
    else:
        signal = "GREEN"
        signal_detail = "no major deterministic risk flag"

    summary = str(data.get("summary") or "").strip()
    summary_is_generic = summary.lower() in GENERIC_MOCK_SUMMARIES or summary.lower().startswith(
        "mock "
    )
    key_thesis = [str(item) for item in data.get("key_thesis") or []]
    main_risks = [str(item) for item in data.get("main_risks") or []]
    if summary and not summary_is_generic:
        detailed_analysis = summary
    else:
        detailed_analysis = " ".join(key_thesis[:2] + main_risks[:2]).strip()

    return {
        "signal": signal,
        "signal_detail": signal_detail,
        "detailed_analysis": detailed_analysis or "No usable portfolio analysis was returned.",
        "rebalancing": [str(item) for item in data.get("action_plan") or []],
        "evidence": {
            "annualized_volatility": volatility,
            "max_drawdown": drawdown,
            "largest_fund_weight": largest_weight,
            "top_sector_weight": top_sector_weight,
            "overlapping_holding_count": overlap_count,
        },
    }


def _parse_position(raw: str) -> dict[str, Any]:
    code, separator, weight_text = str(raw).partition("=")
    code = code.strip()
    if not separator or not code:
        raise argparse.ArgumentTypeError("position must use CODE=AMOUNT, for example 000001=6000")
    try:
        weight = float(weight_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid amount in position {raw!r}") from exc
    if weight <= 0:
        raise argparse.ArgumentTypeError("position amount must be positive")
    return {"code": code, "weight": weight}


def call_agent(
    base_url: str,
    positions: list[dict[str, Any]],
    *,
    real_llm: bool,
    risk_profile: str,
    timeout_seconds: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    request_payload = {
        "positions": positions,
        "client_risk_profile": risk_profile,
        "mock": not real_llm,
        "include_lookthrough": True,
        "max_nav_points": 520,
    }
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/ai/portfolio/analyze",
        data=json.dumps(request_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Agent returned HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot reach Agent at {base_url}: {exc.reason}") from exc

    if body.get("code") != 200 or not isinstance(body.get("data"), dict):
        raise RuntimeError(f"Unexpected Agent response: {body}")
    return body["data"], {"request": request_payload, "coverage": body.get("coverage") or {}}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview the Overview AI Portfolio Analysis widget without changing the frontend."
    )
    parser.add_argument(
        "--agent-url",
        help="Call a running Agent, for example http://127.0.0.1:5003. Omit for sample mode.",
    )
    parser.add_argument(
        "--position",
        action="append",
        type=_parse_position,
        default=[],
        metavar="CODE=AMOUNT",
        help="Fund holding for live mode; repeat this option for multiple funds.",
    )
    parser.add_argument("--real-llm", action="store_true", help="Use real LLM mode in live HTTP mode.")
    parser.add_argument("--risk-profile", default="balanced")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--json", action="store_true", help="Print one machine-readable JSON object.")
    return parser.parse_args(argv[1:])


def _print_human(source: str, data: dict[str, Any], preview: dict[str, Any], context: dict) -> None:
    metrics = data.get("quant_metrics") or {}
    print(f"Source: {source}")
    if context:
        print("Request:")
        print(json.dumps(context.get("request") or {}, ensure_ascii=False, indent=2))

    print("\nAgent evidence:")
    print(f"- annualized volatility: {_percentage(metrics.get('annualized_volatility'))}")
    print(f"- max drawdown: {_percentage(metrics.get('max_drawdown'))}")
    print(f"- diversification benefit: {_percentage(metrics.get('diversification_benefit'))}")
    print(f"- overall rating: {data.get('overall_rating', 'N/A')}")

    print("\nOverview widget preview:")
    print(f"Signal: {preview['signal']} — {preview['signal_detail']}")
    print(f"Detailed analysis: {preview['detailed_analysis']}")
    print("Rebalancing:")
    for item in preview["rebalancing"] or ["No direction returned."]:
        print(f"- {item}")


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        if args.agent_url:
            if not args.position:
                raise ValueError("live mode requires at least one --position CODE=AMOUNT")
            data, context = call_agent(
                args.agent_url,
                args.position,
                real_llm=args.real_llm,
                risk_profile=args.risk_profile,
                timeout_seconds=args.timeout,
            )
            source = f"live Agent endpoint at {args.agent_url}"
        else:
            payload = build_sample_input()
            # Empty mock text deliberately exercises the production deterministic fallback.
            data = run_mock_portfolio_analysis_for_input(payload, mock_response="").to_dict()
            context = {
                "request": {
                    "positions": [
                        {"code": fund.fund_info.code, "weight": fund.requested_weight}
                        for fund in payload.funds
                    ],
                    "client_risk_profile": payload.client_risk_profile,
                    "mock": True,
                }
            }
            source = "production portfolio pipeline + labelled deterministic sample data"

        preview = build_widget_preview(data)
        if args.json:
            print(
                json.dumps(
                    {"source": source, "context": context, "widget": preview, "agent_data": data},
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            _print_human(source, data, preview, context)
        return 0
    except (RuntimeError, ValueError) as exc:
        print(f"preview_portfolio_widget failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
