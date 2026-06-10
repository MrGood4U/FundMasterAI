"""Standalone FundMasterAI Agent backend.

Run this service after the team market/news backends are running. It discovers
their function registries, builds a `FundAnalysisInput`, executes the LLM
engine, and returns frontend-friendly JSON.
"""

from __future__ import annotations

import os
import sys
import json
from pathlib import Path

from flask import Flask, jsonify, request

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fund_llm.adapters.backend_function_client import (  # noqa: E402
    BackendFunctionClient,
    build_fund_input_from_backend_functions,
)
from fund_llm.contracts import AnalysisTraceEvent  # noqa: E402
from fund_llm.fund_routing import build_data_coverage, classify_fund_type  # noqa: E402
from fund_llm.mock_pipeline import run_mock_analysis_for_input  # noqa: E402
from fund_llm.real_pipeline import run_real_analysis_for_input  # noqa: E402


def _truthy(value) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _coverage(payload) -> dict:
    fund_type_profile = classify_fund_type(payload.fund_info.category)
    return {
        "nav_points": len(payload.nav_series),
        "has_top_holdings_weight": payload.top_holdings_weight is not None,
        "has_industry_exposure": bool(payload.industry_exposure),
        "has_news_items": bool(payload.news_items),
        "fund_name": payload.fund_info.name,
        "fund_type": payload.fund_info.category,
        "normalized_fund_type": fund_type_profile.normalized_type,
        "fund_family": fund_type_profile.family,
        "data_coverage": build_data_coverage(payload),
        "data_source": payload.extra_context.get("data_source", ""),
        "available_backend_tools": payload.extra_context.get("available_backend_tools", ""),
        "successful_backend_tools": payload.extra_context.get("successful_backend_tools", ""),
        "errored_backend_tools": payload.extra_context.get("errored_backend_tools", ""),
    }


def _csv_items(value: str) -> list[str]:
    return [item for item in str(value or "").split(",") if item]


def _json_list(value: str) -> list[dict]:
    try:
        parsed = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _build_source_trace(payload) -> list[AnalysisTraceEvent]:
    coverage = build_data_coverage(payload)
    available_tools = _csv_items(payload.extra_context.get("available_backend_tools", ""))
    successful_tools = _csv_items(payload.extra_context.get("successful_backend_tools", ""))
    errored_tools = _csv_items(payload.extra_context.get("errored_backend_tools", ""))
    tool_trace = _json_list(payload.extra_context.get("tool_trace", ""))
    missing_coverage = {
        key: value
        for key, value in coverage.items()
        if value not in {"available", "not_applicable"}
    }
    coverage_status = "warning" if missing_coverage else "success"

    return [
        AnalysisTraceEvent(
            category="backend",
            title="Discovered backend tools",
            detail=(
                "Loaded callable function definitions from the team backend registries, "
                "then selected the fund-related tools needed by the AI engine."
            ),
            status="success" if available_tools else "warning",
            evidence={
                "available_tool_count": len(available_tools),
                "successful_tool_count": len(successful_tools),
                "errored_tool_count": len(errored_tools),
            },
            technical={
                "available_backend_tools": available_tools,
                "successful_backend_tools": successful_tools,
                "errored_backend_tools": errored_tools,
            },
        ),
        AnalysisTraceEvent(
            category="backend",
            title="Loaded real fund history",
            detail=(
                "Fetched NAV history through the backend function registry and used those "
                "records as the quantitative base for return and risk metrics."
            ),
            status="success" if payload.nav_series else "error",
            evidence={
                "fund_code": payload.fund_info.code,
                "nav_points": len(payload.nav_series),
                "start_date": payload.analysis_window.start_date if payload.analysis_window else "",
                "end_date": payload.analysis_window.end_date if payload.analysis_window else "",
            },
            technical={
                "data_source": payload.extra_context.get("data_source", ""),
                "required_function": "get_fund_hist",
                "tool_trace": tool_trace,
            },
        ),
        AnalysisTraceEvent(
            category="backend",
            title="Identified fund profile",
            detail=(
                "Matched the fund name and type from backend basic information, then routed "
                "the analysis with deterministic fund-type rules before calling the LLM."
            ),
            status="success",
            evidence={
                "fund_name": payload.fund_info.name,
                "raw_fund_type": payload.extra_context.get("raw_fund_type", payload.fund_info.category),
                "normalized_fund_type": payload.extra_context.get("normalized_fund_type", ""),
                "fund_family": payload.extra_context.get("fund_family", ""),
            },
            technical={
                "portfolio_year": payload.extra_context.get("portfolio_year", ""),
                "holdings_count": payload.extra_context.get("holdings_count", "0"),
                "news_count": payload.extra_context.get("news_count", "0"),
            },
        ),
        AnalysisTraceEvent(
            category="backend",
            title="Checked backend data coverage",
            detail=(
                "Marked which data categories were available, missing, or not applicable "
                "for this fund type so skipped agents are not treated as neutral signals."
            ),
            status=coverage_status,
            evidence={
                "data_coverage": coverage,
                "missing_or_limited": missing_coverage,
            },
            technical={
                "top_holdings_weight": payload.top_holdings_weight,
                "industry_exposure_count": len(payload.industry_exposure),
                "news_item_count": len(payload.news_items),
            },
        ),
    ]


def create_app() -> Flask:
    app = Flask(__name__)

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = os.getenv("AGENT_CORS_ORIGIN", "*")
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response

    @app.get("/health")
    def health():
        return jsonify({"code": 200, "message": "agent backend ok"}), 200

    @app.get("/api/ai/functions")
    def ai_functions():
        client = BackendFunctionClient()
        include_portfolio = _truthy(request.args.get("include_portfolio", "false"))
        client.discover_fund_tools(include_portfolio=include_portfolio)
        return jsonify(
            {
                "code": 200,
                "data": [item.spec for item in client.functions.values()],
                "message": "success",
            }
        ), 200

    @app.route("/api/ai/fund/analyze", methods=["POST", "OPTIONS"])
    def analyze_fund():
        if request.method == "OPTIONS":
            return jsonify({"code": 200, "message": "ok"}), 200

        body = request.get_json(silent=True) or {}
        code = str(body.get("code") or body.get("fund_code") or "").strip()
        if not code:
            return jsonify({"code": 400, "data": None, "message": "code is required"}), 400

        try:
            payload = build_fund_input_from_backend_functions(
                code,
                start_date=body.get("start_date"),
                end_date=body.get("end_date"),
                max_nav_points=int(body.get("max_nav_points") or 260),
                portfolio_year=body.get("portfolio_year"),
                top_holdings_n=int(body.get("top_holdings_n") or 10),
                max_news_items=int(body.get("max_news_items") or 8),
                client_risk_profile=str(body.get("client_risk_profile") or "balanced"),
                fund_name_fallback=str(body.get("fund_name") or ""),
            )

            use_mock = _truthy(body.get("mock", os.getenv("LLM_MOCK_MODE", "false")))
            if use_mock:
                result = run_mock_analysis_for_input(
                    payload,
                    mock_response="Mock LLM narrative generated for backend function-registry integration.",
                    max_parallel_agents=int(body.get("max_parallel_agents") or 5),
                )
                result.metadata["llm_mode"] = "mock"
            else:
                result = run_real_analysis_for_input(
                    payload,
                    timeout_seconds=int(body.get("llm_timeout_seconds") or os.getenv("LLM_TIMEOUT_SECONDS", "60")),
                    max_parallel_agents=int(body.get("max_parallel_agents") or 5),
                )
                result.metadata["llm_mode"] = "real"

            result.analysis_trace = _build_source_trace(payload) + result.analysis_trace

            return jsonify(
                {
                    "code": 200,
                    "data": result.to_dict(),
                    "coverage": _coverage(payload),
                    "message": "success",
                }
            ), 200
        except ValueError as exc:
            return jsonify({"code": 422, "data": None, "message": str(exc)}), 422
        except Exception as exc:
            return jsonify({"code": 500, "data": None, "message": str(exc)}), 500

    return app


if __name__ == "__main__":
    port = int(os.getenv("AGENT_HTTP_PORT", "5003"))
    debug = _truthy(os.getenv("AGENT_DEBUG", "true"))
    use_reloader = _truthy(os.getenv("AGENT_RELOAD", str(debug).lower()))
    create_app().run(
        host=os.getenv("AGENT_HTTP_HOST", "127.0.0.1"),
        port=port,
        debug=debug,
        use_reloader=use_reloader,
    )
