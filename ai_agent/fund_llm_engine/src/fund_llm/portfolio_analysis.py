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

    common_dates = None
    for fund in funds:
        dates = set(_nav_by_date(fund.nav_series))
        common_dates = dates if common_dates is None else (common_dates & dates)

    sorted_dates = sorted(common_dates or [])
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
        fund_type_profile = classify_fund_type(fund.fund_info.category)
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
