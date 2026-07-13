"""Sector-level cross-fund comparison view (Phase B1).

把多只基金的行业暴露聚合成「行业层」横向比较：每个行业一行，列出各基金
的暴露、平均暴露和最大暴露，用于回答"这几只基金在行业上怎么分布、
哪里撞车"。本模块只做确定性计算，不调用 LLM，不发 HTTP 请求。

按 implementation_plan 的边界，这是轻量视图：不引入重量级
`SectorAnalysisInput` 契约，行业状态语义（`available` /
`insufficient_data` / `not_applicable`）与单基金 `SectorAgent` 保持一致。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from fund_llm.contracts import FundInfo
from fund_llm.fund_routing import classify_fund_type


@dataclass
class SectorViewFund:
    """Per-fund input for the sector comparison view."""

    fund_info: FundInfo
    industry_exposure: Dict[str, float] = field(default_factory=dict)


def classify_sector_status(fund: SectorViewFund) -> str:
    """Same semantics as SectorAgent: not_applicable / insufficient_data / available."""
    profile = classify_fund_type(fund.fund_info.category, fund.fund_info.name)
    if not profile.sector_analysis_applicable:
        return "not_applicable"
    if not fund.industry_exposure:
        return "insufficient_data"
    return "available"


def build_sector_view(funds: List[SectorViewFund], top_n_sectors: int = 15) -> Dict[str, object]:
    """Build the deterministic sector-level comparison structure."""
    if not funds:
        raise ValueError("Sector view needs at least one fund code.")

    fund_rows: List[Dict[str, object]] = []
    available_funds: List[SectorViewFund] = []
    funds_without_data: List[str] = []

    for fund in funds:
        profile = classify_fund_type(fund.fund_info.category, fund.fund_info.name)
        status = classify_sector_status(fund)
        ranked = sorted(fund.industry_exposure.items(), key=lambda item: -item[1])
        fund_rows.append(
            {
                "code": fund.fund_info.code,
                "name": fund.fund_info.name,
                "fund_type": fund.fund_info.category,
                "normalized_fund_type": profile.normalized_type,
                "sector_status": status,
                "sector_count": len(ranked),
                "top_sector": ranked[0][0] if ranked else "",
                "top_sector_weight": round(ranked[0][1], 6) if ranked else 0.0,
                "top_sectors": [
                    {"sector": sector, "weight": round(weight, 6)}
                    for sector, weight in ranked[:3]
                ],
            }
        )
        if status == "available":
            available_funds.append(fund)
        else:
            funds_without_data.append(fund.fund_info.code)

    all_sectors = sorted({sector for fund in available_funds for sector in fund.industry_exposure})
    matrix_rows: List[Dict[str, object]] = []
    for sector in all_sectors:
        exposures = {
            fund.fund_info.code: round(fund.industry_exposure[sector], 6)
            for fund in available_funds
            if sector in fund.industry_exposure
        }
        weights = list(exposures.values())
        max_fund = max(exposures, key=exposures.get)
        matrix_rows.append(
            {
                "sector": sector,
                "exposures": exposures,
                "funds_holding": len(exposures),
                # 平均口径：只对提供了行业数据的基金做等权平均（横向比较视图，
                # 不引入用户权重；组合加权口径在 portfolio 接口的 industry_lookthrough）。
                "average_weight": round(sum(weights) / len(available_funds), 6),
                "max_weight": round(max(weights), 6),
                "max_fund": max_fund,
            }
        )
    matrix_rows.sort(key=lambda row: -float(row["average_weight"]))

    common_sectors = [
        row["sector"] for row in matrix_rows if int(row["funds_holding"]) >= 2
    ]

    if not available_funds:
        overall_status = "missing"
    elif funds_without_data:
        overall_status = "partial"
    else:
        overall_status = "available"

    return {
        "status": overall_status,
        "funds": fund_rows,
        "funds_with_data": [fund.fund_info.code for fund in available_funds],
        "funds_without_data": funds_without_data,
        "sector_matrix": matrix_rows[:top_n_sectors],
        "sector_total_count": len(matrix_rows),
        "common_sectors": common_sectors,
    }
