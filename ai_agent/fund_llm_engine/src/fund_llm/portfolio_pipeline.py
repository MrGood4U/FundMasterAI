"""Portfolio analysis orchestration (Phase A1).

流程：日期对齐 -> 合成组合净值 -> 组合/成分指标 -> PortfolioChiefAgent 总评。
mock 与 real 共用同一条确定性计算路径，只是 LLM client 不同。
"""

from __future__ import annotations

from typing import List, Optional

from fund_llm.agents.portfolio_chief_agent import PortfolioChiefAgent
from fund_llm.contracts import (
    AnalysisTraceEvent,
    PortfolioAnalysisInput,
    PortfolioAnalysisResult,
)
from fund_llm.llm_client import LLMClient, MockLLMClient
from fund_llm.portfolio_analysis import (
    align_common_dates,
    build_constituent_metrics,
    build_portfolio_quant_metrics,
    compose_portfolio_nav,
)


def _rounded(value):
    return round(value, 4) if isinstance(value, float) else value


def _build_alignment_trace(payload: PortfolioAnalysisInput, common_dates: List[str]) -> AnalysisTraceEvent:
    return AnalysisTraceEvent(
        category="feature",
        title="Aligned constituent NAV calendars",
        detail=(
            "Intersected the NAV dates of all constituent funds so daily returns are "
            "computed on the same shared trading calendar."
        ),
        status="success",
        evidence={
            "fund_count": len(payload.funds),
            "shared_nav_points": len(common_dates),
            "shared_start_date": common_dates[0],
            "shared_end_date": common_dates[-1],
        },
        technical={
            "per_fund_nav_points": {
                fund.fund_info.code: len(fund.nav_series) for fund in payload.funds
            },
            "weights": {fund.fund_info.code: round(fund.weight, 6) for fund in payload.funds},
        },
    )


def _build_composition_trace(quant_metrics: dict) -> AnalysisTraceEvent:
    return AnalysisTraceEvent(
        category="feature",
        title="Composed weighted portfolio NAV",
        detail=(
            "Compounded the weighted average of constituent daily returns into one "
            "fixed-weight (daily rebalanced) portfolio NAV, then calculated return, "
            "volatility, drawdown, and diversification metrics on it."
        ),
        status="success",
        evidence={
            "total_return": _rounded(quant_metrics.get("total_return")),
            "annualized_volatility": _rounded(quant_metrics.get("annualized_volatility")),
            "max_drawdown": _rounded(quant_metrics.get("max_drawdown")),
            "sharpe_ratio": _rounded(quant_metrics.get("sharpe_ratio")),
            "diversification_benefit": _rounded(quant_metrics.get("diversification_benefit")),
        },
        technical={
            "weighted_average_volatility": _rounded(quant_metrics.get("weighted_average_volatility")),
            "sample_size": quant_metrics.get("sample_size"),
        },
    )


def _build_aggregation_trace(chief_view: dict) -> AnalysisTraceEvent:
    return AnalysisTraceEvent(
        category="aggregation",
        title="Aggregated portfolio view",
        detail=(
            "Scored the portfolio deterministically from the composed metrics and asked the "
            "LLM only to explain the already-computed evidence."
        ),
        status="success",
        evidence={
            "overall_rating": chief_view["overall_rating"],
            "overall_score": chief_view["overall_score"],
            "quant_metrics_reliability": chief_view["quant_metrics_reliability"],
        },
        technical={
            "summary_source": chief_view["summary_source"],
        },
    )


def run_portfolio_analysis_for_input(
    payload: PortfolioAnalysisInput,
    llm_client,
) -> PortfolioAnalysisResult:
    missing_fields = payload.validate_required_fields()
    if missing_fields:
        raise ValueError(f"Portfolio input is missing required fields: {', '.join(missing_fields)}.")

    common_dates = align_common_dates(payload.funds)
    portfolio_nav = compose_portfolio_nav(payload.funds, common_dates)
    constituents = build_constituent_metrics(payload.funds, common_dates)
    quant_metrics = build_portfolio_quant_metrics(portfolio_nav, constituents)

    weights_rescaled = payload.extra_context.get("weights_rescaled", "false") == "true"
    chief = PortfolioChiefAgent(llm_client)
    chief_view = chief.aggregate(
        quant_metrics=quant_metrics,
        constituents=constituents,
        client_risk_profile=payload.client_risk_profile,
        weights_rescaled=weights_rescaled,
    )

    metadata = {
        "analysis_level": "portfolio",
        "fund_count": str(len(payload.funds)),
        "shared_nav_points": str(len(common_dates)),
        "shared_start_date": common_dates[0],
        "shared_end_date": common_dates[-1],
        "weights_rescaled": str(weights_rescaled).lower(),
        "client_risk_profile": payload.client_risk_profile,
        "summary_source": chief_view["summary_source"],
        "quant_metrics_sample_size": str(int(quant_metrics.get("sample_size", 0))),
        "quant_metrics_reliability": chief_view["quant_metrics_reliability"],
    }

    trace = [
        _build_alignment_trace(payload, common_dates),
        _build_composition_trace(quant_metrics),
        _build_aggregation_trace(chief_view),
    ]

    return PortfolioAnalysisResult(
        request_id=payload.request_id,
        overall_rating=chief_view["overall_rating"],
        overall_score=chief_view["overall_score"],
        summary=chief_view["summary"],
        score_explanation=chief_view["score_explanation"],
        key_thesis=chief_view["key_thesis"],
        main_risks=chief_view["main_risks"],
        action_plan=chief_view["action_plan"],
        quant_metrics=quant_metrics,
        constituents=constituents,
        missing_fields=[],
        metadata=metadata,
        analysis_trace=trace,
    )


def run_mock_portfolio_analysis_for_input(
    payload: PortfolioAnalysisInput,
    mock_response: str = "Mock portfolio narrative.",
) -> PortfolioAnalysisResult:
    result = run_portfolio_analysis_for_input(payload, MockLLMClient(mock_response))
    result.metadata["llm_mode"] = "mock"
    return result


def run_real_portfolio_analysis_for_input(
    payload: PortfolioAnalysisInput,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    timeout_seconds: Optional[int] = None,
) -> PortfolioAnalysisResult:
    llm_client = LLMClient(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout_seconds=timeout_seconds,
    )
    result = run_portfolio_analysis_for_input(payload, llm_client)
    result.metadata.update(
        {
            "llm_mode": "real",
            "llm_model": llm_client.model,
            "llm_base_url": llm_client.base_url,
        }
    )
    return result
