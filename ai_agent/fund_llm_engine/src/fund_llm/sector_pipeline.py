"""Sector-level view orchestration (Phase B1).

流程：per-fund 行业数据 -> 确定性行业矩阵 -> LLM 只解释已算好的比较结果。
LLM 失败或输出不完整时回退到确定性摘要，与其他管线的防幻觉策略一致。
"""

from __future__ import annotations

from typing import Dict, List, Optional

from fund_llm import config
from fund_llm.agents.chief_agent import _summary_looks_incomplete
from fund_llm.contracts import AnalysisTraceEvent
from fund_llm.llm_client import LLMClient, MockLLMClient
from fund_llm.sector_view import SectorViewFund, build_sector_view


def _build_deterministic_summary(view: Dict[str, object]) -> str:
    fund_count = len(view["funds"])
    with_data = view["funds_with_data"]
    without_data = view["funds_without_data"]
    matrix = view["sector_matrix"]

    parts = [
        f"Sector comparison covers {fund_count} fund(s); "
        f"{len(with_data)} provided industry exposure data."
    ]
    if matrix:
        top_row = matrix[0]
        parts.append(
            f"The heaviest average sector is {top_row['sector']} "
            f"(average {top_row['average_weight']:.2%}, held by {top_row['funds_holding']} fund(s), "
            f"max {top_row['max_weight']:.2%} in {top_row['max_fund']})."
        )
    if view["common_sectors"]:
        shared = ", ".join(view["common_sectors"][:3])
        parts.append(f"Sectors shared by two or more funds include {shared}.")
    if without_data:
        parts.append(
            f"No sector conclusion is drawn for {', '.join(without_data)} because industry "
            "data is unavailable or sector analysis is not applicable to the fund type."
        )
    parts.append("Use this comparison as sector-level context, not as a standalone recommendation.")
    return " ".join(parts)


def _build_summary_prompts(view: Dict[str, object]) -> tuple:
    fund_lines = "\n".join(
        f"- {row['name']} ({row['code']}) type={row['normalized_fund_type']} "
        f"status={row['sector_status']} top_sector={row['top_sector'] or 'N/A'} "
        f"top_weight={row['top_sector_weight']:.2%} sector_count={row['sector_count']}"
        for row in view["funds"]
    )
    matrix_lines = "\n".join(
        f"- {row['sector']}: avg={row['average_weight']:.2%}, funds_holding={row['funds_holding']}, "
        f"max={row['max_weight']:.2%} ({row['max_fund']}), exposures={row['exposures']}"
        for row in view["sector_matrix"][:8]
    )
    system_prompt = (
        "You are a sector allocation analyst comparing multiple funds. Explain where their "
        "industry exposures concentrate and overlap, using only the provided comparison table. "
        "Respond in English only: sector and fund names may be Chinese, but the narrative must be English. "
        "Do not infer sectors or holdings from fund names or outside knowledge. "
        "State clearly when a fund has no usable sector data instead of guessing. "
        "Keep the summary under 140 words and end with a complete sentence."
    )
    user_prompt = (
        f"Funds:\n{fund_lines}\n\n"
        f"Sector comparison matrix (top rows):\n{matrix_lines or '- No sector data available.'}\n\n"
        f"Common sectors held by 2+ funds: {view['common_sectors'][:5]}\n"
        "Please write a concise sector-level comparison in one or two short paragraphs."
    )
    return system_prompt, user_prompt


def _build_sector_trace(view: Dict[str, object], summary_source: str) -> List[AnalysisTraceEvent]:
    return [
        AnalysisTraceEvent(
            category="feature",
            title="Built sector comparison matrix",
            detail=(
                "Collected per-fund industry exposure, marked funds without usable sector data, "
                "and ranked sectors by average exposure across the requested funds."
            ),
            status="success" if view["status"] != "missing" else "warning",
            evidence={
                "status": view["status"],
                "fund_count": len(view["funds"]),
                "funds_with_data": view["funds_with_data"],
                "funds_without_data": view["funds_without_data"],
                "sector_total_count": view["sector_total_count"],
                "common_sector_count": len(view["common_sectors"]),
            },
            technical={
                "top_matrix_rows": view["sector_matrix"][:3],
            },
        ),
        AnalysisTraceEvent(
            category="aggregation",
            title="Summarized sector-level view",
            detail=(
                "Generated the sector comparison narrative strictly from the computed matrix; "
                "funds without sector data are reported as unavailable instead of guessed."
            ),
            status="success",
            evidence={"summary_source": summary_source},
            technical={},
        ),
    ]


def run_sector_view_for_funds(
    funds: List[SectorViewFund],
    llm_client,
    context: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    view = build_sector_view(funds)

    summary_source = "llm"
    system_prompt, user_prompt = _build_summary_prompts(view)
    try:
        summary = llm_client.chat(system_prompt, user_prompt, max_tokens=900)
    except Exception:
        summary = ""
        summary_source = "deterministic_fallback"
    if (
        not getattr(llm_client, "is_mock", False)
        and _summary_looks_incomplete(summary)
    ):
        summary = ""
        summary_source = "deterministic_fallback"
    if not summary:
        summary = _build_deterministic_summary(view)

    context = dict(context or {})
    metadata = {
        "analysis_level": "sector",
        "fund_count": str(len(view["funds"])),
        "sector_view_status": str(view["status"]),
        "funds_with_data_count": str(len(view["funds_with_data"])),
        "summary_source": summary_source,
        "data_source": str(context.get("data_source", "")),
        "prompt_version": config.PROMPT_VERSION,
    }

    codes = "-".join(row["code"] for row in view["funds"])
    return {
        "request_id": f"sector-view-{codes}",
        "status": view["status"],
        "funds": view["funds"],
        "sector_matrix": view["sector_matrix"],
        "sector_total_count": view["sector_total_count"],
        "common_sectors": view["common_sectors"],
        "funds_with_data": view["funds_with_data"],
        "funds_without_data": view["funds_without_data"],
        "summary": summary,
        "metadata": metadata,
        "analysis_trace": [event.to_dict() for event in _build_sector_trace(view, summary_source)],
    }


def run_mock_sector_view_for_funds(
    funds: List[SectorViewFund],
    context: Optional[Dict[str, object]] = None,
    mock_response: str = "Mock sector comparison narrative.",
) -> Dict[str, object]:
    result = run_sector_view_for_funds(funds, MockLLMClient(mock_response), context=context)
    result["metadata"]["llm_mode"] = "mock"
    return result


def run_real_sector_view_for_funds(
    funds: List[SectorViewFund],
    context: Optional[Dict[str, object]] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    timeout_seconds: Optional[int] = None,
) -> Dict[str, object]:
    llm_client = LLMClient(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout_seconds=timeout_seconds,
    )
    result = run_sector_view_for_funds(funds, llm_client, context=context)
    result["metadata"].update(
        {
            "llm_mode": "real",
            "llm_model": llm_client.model,
            "llm_base_url": llm_client.base_url,
        }
    )
    return result
