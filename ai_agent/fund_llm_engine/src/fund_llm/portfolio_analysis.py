"""Portfolio-level NAV composition and deterministic metrics (Phase A1).

职责：把多只成分基金的净值序列按「日期交集对齐 + 固定权重每日再平衡」
合成一条组合净值，然后复用 `feature_builder` 的指标函数计算组合层指标。
本模块只做确定性计算，不调用 LLM，也不发任何 HTTP 请求。
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from fund_llm.contracts import (
    NavPoint,
    PortfolioConstituentMetrics,
    PortfolioFundData,
    PortfolioPosition,
)
from fund_llm.feature_builder import (
    _asset_bucket_weight,
    _holding_weight,
    _normalize_asset_allocation,
    calculate_annualized_return,
    calculate_annualized_volatility,
    calculate_calmar_ratio,
    calculate_max_drawdown,
    calculate_period_return,
    calculate_positive_period_ratio,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_trailing_annualized_volatility,
    calculate_trailing_max_drawdown,
    calculate_trailing_period_return,
    TRADING_WINDOWS,
)
from fund_llm.fund_routing import classify_fund_type

# 低于这个共同交易日数量时，组合层年化指标基本没有意义，直接结构化报错
# 而不是输出失真数值（与单基金路径的防幻觉原则一致）。
MIN_OVERLAP_POINTS = 30


def normalize_positions(positions: List[PortfolioPosition]) -> Tuple[List[PortfolioPosition], bool]:
    """Validate raw positions and normalize weights to sum to 1.0.

    Returns the normalized positions plus a flag telling whether the input
    weights had to be rescaled (so the API can surface that in metadata).
    Raises ValueError with a frontend-friendly message on invalid input.
    """
    if not positions:
        raise ValueError("Portfolio positions are required. Provide at least one {code, weight} item.")

    seen_codes = set()
    for position in positions:
        if not position.code:
            raise ValueError("Every portfolio position needs a fund code.")
        if position.code in seen_codes:
            raise ValueError(f"Fund code {position.code!r} appears more than once in the portfolio.")
        seen_codes.add(position.code)
        if position.weight <= 0:
            raise ValueError(
                f"Portfolio weight for fund {position.code!r} must be positive, got {position.weight}."
            )

    total_weight = sum(position.weight for position in positions)
    was_rescaled = abs(total_weight - 1.0) > 1e-6
    normalized = [
        PortfolioPosition(
            code=position.code,
            weight=position.weight / total_weight,
            name=position.name,
        )
        for position in positions
    ]
    return normalized, was_rescaled


def _nav_by_date(nav_series: List[NavPoint]) -> Dict[str, float]:
    return {point.date: point.nav for point in nav_series if point.nav is not None}


def intersect_nav_dates(funds: List[PortfolioFundData]) -> List[str]:
    """Sorted intersection of NAV dates across funds, without any length check.

    对齐口径的唯一实现：adapter 构造 `analysis_window` 和管线做净值合成
    必须使用同一份交集逻辑，避免"输入窗口"和"实际计算窗口"不一致。
    """
    if not funds:
        return []
    common_dates = None
    for fund in funds:
        dates = set(_nav_by_date(fund.nav_series))
        common_dates = dates if common_dates is None else (common_dates & dates)
    return sorted(common_dates or [])


def align_common_dates(
    funds: List[PortfolioFundData],
    min_overlap_points: int = MIN_OVERLAP_POINTS,
) -> List[str]:
    """Return the sorted intersection of NAV dates across all constituent funds.

    Raises ValueError when the shared window is too short for meaningful
    portfolio metrics, naming the funds so the caller can explain the failure.
    """
    if not funds:
        raise ValueError("Portfolio composition needs at least one constituent fund.")

    sorted_dates = intersect_nav_dates(funds)
    if len(sorted_dates) < min_overlap_points:
        detail = ", ".join(
            f"{fund.fund_info.code}({len(fund.nav_series)} NAV points)" for fund in funds
        )
        raise ValueError(
            "Constituent funds only share "
            f"{len(sorted_dates)} common NAV date(s), below the minimum of {min_overlap_points} "
            f"needed for portfolio metrics. Funds: {detail}."
        )
    return sorted_dates


def compose_portfolio_nav(
    funds: List[PortfolioFundData],
    common_dates: List[str],
) -> List[NavPoint]:
    """Compose the portfolio NAV with fixed weights (daily rebalanced).

    组合每日收益 = Σ 权重_i × 成分基金当日收益，再逐日复利成净值序列，
    起始净值恒为 1.0。等价于每天把仓位再平衡回目标权重：

    - 语义上贴合用户输入的「目标配置」（60/40 始终是 60/40）；
    - 数学上保证组合波动率 ≤ 成分波动率的加权线性平均（Minkowski 不等式），
      因此 `diversification_benefit` 恒 ≥ 0，可作为稳定的分散化证据。

    若改用买入持有（首日归一化后加权），权重会随净值漂移，
    高收益成分的权重越长越大，分散化效应会被漂移掩盖，不利于解释。
    """
    if not common_dates:
        raise ValueError("Cannot compose a portfolio NAV without aligned dates.")

    nav_maps: List[Tuple[float, Dict[str, float]]] = []
    for fund in funds:
        nav_map = _nav_by_date(fund.nav_series)
        for date in common_dates:
            if nav_map[date] == 0:
                raise ValueError(
                    f"Fund {fund.fund_info.code!r} has a zero NAV on {date}, cannot compute returns."
                )
        nav_maps.append((fund.weight, nav_map))

    portfolio_points = [NavPoint(date=common_dates[0], nav=1.0)]
    portfolio_nav = 1.0
    for previous_date, current_date in zip(common_dates[:-1], common_dates[1:]):
        daily_return = sum(
            weight * ((nav_map[current_date] / nav_map[previous_date]) - 1.0)
            for weight, nav_map in nav_maps
        )
        portfolio_nav *= 1.0 + daily_return
        portfolio_points.append(NavPoint(date=current_date, nav=round(portfolio_nav, 8)))
    return portfolio_points


def _aligned_fund_series(fund: PortfolioFundData, common_dates: List[str]) -> List[NavPoint]:
    nav_map = _nav_by_date(fund.nav_series)
    return [NavPoint(date=date, nav=nav_map[date]) for date in common_dates]


def build_constituent_metrics(
    funds: List[PortfolioFundData],
    common_dates: List[str],
) -> List[PortfolioConstituentMetrics]:
    """Per-fund metrics computed on the shared aligned window for fair comparison."""
    constituents = []
    for fund in funds:
        aligned_series = _aligned_fund_series(fund, common_dates)
        fund_type_profile = classify_fund_type(
            fund.fund_info.category,
            fund.fund_info.name,
        )
        constituents.append(
            PortfolioConstituentMetrics(
                code=fund.fund_info.code,
                name=fund.fund_info.name,
                fund_type=fund.fund_info.category,
                normalized_fund_type=fund_type_profile.normalized_type,
                weight=round(fund.weight, 6),
                nav_points=len(aligned_series),
                total_return=round(calculate_period_return(aligned_series), 6),
                annualized_return=round(calculate_annualized_return(aligned_series), 6),
                annualized_volatility=round(calculate_annualized_volatility(aligned_series), 6),
                max_drawdown=round(calculate_max_drawdown(aligned_series), 6),
                sharpe_ratio=round(calculate_sharpe_ratio(aligned_series), 6),
            )
        )
    return constituents


def build_portfolio_quant_metrics(
    portfolio_nav: List[NavPoint],
    constituents: List[PortfolioConstituentMetrics],
) -> Dict[str, float]:
    """Portfolio quant metrics with the same key names as the fund-level path.

    额外携带分散化证据：
    - weighted_average_volatility：成分基金波动率按权重的线性平均；
    - diversification_benefit：线性平均波动率 - 组合实际波动率。
      固定权重每日再平衡下该值恒 ≥ 0；成分相关性越低，分散化收益越大，
      完全同涨同跌时为 0。
    """
    portfolio_volatility = calculate_annualized_volatility(portfolio_nav)
    weighted_average_volatility = sum(
        item.weight * item.annualized_volatility for item in constituents
    )

    metrics = {
        "total_return": calculate_period_return(portfolio_nav),
        "annualized_return": calculate_annualized_return(portfolio_nav),
        "annualized_volatility": portfolio_volatility,
        "max_drawdown": calculate_max_drawdown(portfolio_nav),
        "sharpe_ratio": calculate_sharpe_ratio(portfolio_nav),
        "sortino_ratio": calculate_sortino_ratio(portfolio_nav),
        "calmar_ratio": calculate_calmar_ratio(portfolio_nav),
        "positive_period_ratio": calculate_positive_period_ratio(portfolio_nav),
        "weighted_average_volatility": weighted_average_volatility,
        "diversification_benefit": weighted_average_volatility - portfolio_volatility,
    }
    for window_name, lookback_periods in TRADING_WINDOWS.items():
        window_return = calculate_trailing_period_return(portfolio_nav, lookback_periods)
        if window_return is not None:
            metrics[f"return_{window_name}"] = window_return
        window_drawdown = calculate_trailing_max_drawdown(portfolio_nav, lookback_periods)
        if window_drawdown is not None:
            metrics[f"max_drawdown_{window_name}"] = window_drawdown
        window_volatility = calculate_trailing_annualized_volatility(portfolio_nav, lookback_periods)
        if window_volatility is not None:
            metrics[f"annualized_volatility_{window_name}"] = window_volatility

    rounded = {key: round(value, 6) for key, value in metrics.items()}
    rounded["sample_size"] = float(len(portfolio_nav))
    return rounded


def _lookthrough_status(funds_with_data: List[str], total_funds: int) -> str:
    if not funds_with_data:
        return "missing"
    if len(funds_with_data) < total_funds:
        return "partial"
    return "available"


def build_holdings_lookthrough(
    funds: List[PortfolioFundData],
    top_n: int = 10,
) -> Dict[str, object]:
    """Merge constituent top holdings into portfolio-level real exposure.

    每条持仓对组合的贡献 = 基金权重 × 该持仓占基金净值比例。
    同一只股票在多只基金中出现时合并贡献，并记入 overlapping_holdings，
    用于发现「几只基金其实重仓同一只票」的隐性集中。

    披露口径限制：公募季报只披露前十大持仓，所以这是部分穿透，
    `disclosed_weight_total` 表示可穿透部分占组合的比例，剩余仓位未知。
    """
    contributions: Dict[str, Dict[str, object]] = {}
    funds_with_data: List[str] = []
    funds_without_data: List[str] = []

    for fund in funds:
        if not fund.top_holdings:
            funds_without_data.append(fund.fund_info.code)
            continue
        funds_with_data.append(fund.fund_info.code)
        for row in fund.top_holdings:
            weight_in_fund = _holding_weight(row)
            if weight_in_fund is None:
                continue
            stock_code = str(row.get("stock_code") or row.get("code") or "").strip()
            stock_name = str(row.get("stock_name") or row.get("name") or "").strip()
            key = stock_code or stock_name
            if not key:
                continue
            entry = contributions.setdefault(
                key,
                {
                    "stock_code": stock_code,
                    "stock_name": stock_name,
                    "portfolio_weight": 0.0,
                    "held_by": [],
                },
            )
            entry["portfolio_weight"] += fund.weight * weight_in_fund
            entry["held_by"].append(
                {
                    "fund_code": fund.fund_info.code,
                    "weight_in_fund": round(weight_in_fund, 6),
                }
            )

    ranked = sorted(contributions.values(), key=lambda item: -float(item["portfolio_weight"]))
    for entry in ranked:
        entry["portfolio_weight"] = round(float(entry["portfolio_weight"]), 6)
    overlapping = [entry for entry in ranked if len(entry["held_by"]) >= 2]

    return {
        "status": _lookthrough_status(funds_with_data, len(funds)),
        "disclosure_basis": "quarterly_top10_holdings",
        "funds_with_data": funds_with_data,
        "funds_without_data": funds_without_data,
        "top_holdings": ranked[:top_n],
        "overlapping_holdings": overlapping[:top_n],
        "combined_top_weight": round(
            sum(float(entry["portfolio_weight"]) for entry in ranked[:top_n]), 6
        ),
        "disclosed_weight_total": round(
            sum(float(entry["portfolio_weight"]) for entry in ranked), 6
        ),
    }


def build_industry_lookthrough(
    funds: List[PortfolioFundData],
    top_n: int = 10,
) -> Dict[str, object]:
    """Merge constituent industry exposure into a portfolio-level sector view.

    组合行业暴露 = Σ 基金权重 × 该基金行业占比；同时保留 per-fund 明细
    供前端做横向对比。缺行业数据的基金（含债券基金）列入
    funds_without_data，不伪造行业占比。
    """
    aggregate: Dict[str, float] = {}
    per_fund_exposure: Dict[str, Dict[str, float]] = {}
    funds_with_data: List[str] = []
    funds_without_data: List[str] = []

    for fund in funds:
        if not fund.industry_exposure:
            funds_without_data.append(fund.fund_info.code)
            continue
        funds_with_data.append(fund.fund_info.code)
        per_fund_exposure[fund.fund_info.code] = {
            sector: round(exposure, 6) for sector, exposure in fund.industry_exposure.items()
        }
        for sector, exposure in fund.industry_exposure.items():
            aggregate[sector] = aggregate.get(sector, 0.0) + fund.weight * exposure

    ranked_sectors = sorted(aggregate.items(), key=lambda item: -item[1])
    top_sectors = [
        {"sector": sector, "portfolio_weight": round(weight, 6)}
        for sector, weight in ranked_sectors[:top_n]
    ]

    return {
        "status": _lookthrough_status(funds_with_data, len(funds)),
        "funds_with_data": funds_with_data,
        "funds_without_data": funds_without_data,
        "aggregate_exposure": {sector: round(weight, 6) for sector, weight in ranked_sectors},
        "top_sectors": top_sectors,
        "top_sector_weight": round(ranked_sectors[0][1], 6) if ranked_sectors else 0.0,
        "per_fund_exposure": per_fund_exposure,
    }


def build_asset_allocation_lookthrough(funds: List[PortfolioFundData]) -> Dict[str, object]:
    """Merge constituent asset allocation into portfolio stock/bond/cash buckets."""
    merged: Dict[str, float] = {}
    funds_with_data: List[str] = []
    funds_without_data: List[str] = []

    for fund in funds:
        allocation = _normalize_asset_allocation(fund.asset_allocation)
        if not allocation:
            funds_without_data.append(fund.fund_info.code)
            continue
        funds_with_data.append(fund.fund_info.code)
        for asset_name, weight in allocation.items():
            merged[asset_name] = merged.get(asset_name, 0.0) + fund.weight * weight

    buckets = {
        "stock": _asset_bucket_weight(merged, ["股票", "stock", "equity", "权益"]),
        "bond": _asset_bucket_weight(merged, ["债券", "bond", "固定收益", "fixedincome"]),
        "cash": _asset_bucket_weight(merged, ["现金", "cash", "货币", "money"]),
    }
    buckets["other"] = max(0.0, sum(merged.values()) - sum(buckets.values()))

    return {
        "status": _lookthrough_status(funds_with_data, len(funds)),
        "funds_with_data": funds_with_data,
        "funds_without_data": funds_without_data,
        "aggregate_allocation": {name: round(weight, 6) for name, weight in merged.items()},
        "buckets": {name: round(weight, 6) for name, weight in buckets.items()},
    }
