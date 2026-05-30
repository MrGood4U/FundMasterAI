"""Standalone FundMasterAI Agent backend.

Run this service after the team market/news backends are running. It discovers
their function registries, builds a `FundAnalysisInput`, executes the LLM
engine, and returns frontend-friendly JSON.
"""

from __future__ import annotations

import os
import sys
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
from fund_llm.mock_pipeline import run_mock_analysis_for_input  # noqa: E402
from fund_llm.real_pipeline import run_real_analysis_for_input  # noqa: E402


def _truthy(value) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _coverage(payload) -> dict:
    return {
        "nav_points": len(payload.nav_series),
        "has_top_holdings_weight": payload.top_holdings_weight is not None,
        "has_industry_exposure": bool(payload.industry_exposure),
        "has_news_items": bool(payload.news_items),
        "fund_name": payload.fund_info.name,
        "fund_type": payload.fund_info.category,
        "data_source": payload.extra_context.get("data_source", ""),
        "successful_backend_tools": payload.extra_context.get("successful_backend_tools", ""),
        "errored_backend_tools": payload.extra_context.get("errored_backend_tools", ""),
    }


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

            return jsonify(
                {
                    "code": 200,
                    "data": result.to_dict(),
                    "coverage": _coverage(payload),
                    "message": "success",
                }
            ), 200
        except Exception as exc:
            return jsonify({"code": 500, "data": None, "message": str(exc)}), 500

    return app


if __name__ == "__main__":
    port = int(os.getenv("AGENT_HTTP_PORT", "5003"))
    create_app().run(host=os.getenv("AGENT_HTTP_HOST", "127.0.0.1"), port=port, debug=True)
