from math import sqrt
from typing import Any, Callable, Dict, List, Optional

from fund_llm.contracts import FundAnalysisInput, FundFeaturePack, NavPoint
from fund_llm.fund_routing import (
    AVAILABLE,
    MISSING,
    MISSING_BACKEND_CAPABILITY,
    classify_fund_type,
    build_data_coverage,
)
from fund_llm.ratios import canonical_fraction, holding_weight_fraction

TRADING_WINDOWS = {
    "1m": 21,
    "3m": 63,
    "6m": 126,
    "1y": 252,
}

TRADING_DAYS_PER_YEAR = 252
# 年化无风险利率假设，约等于中国短期国债收益率，用于 Sharpe / Sortino 等风险调整指标。
# 这些指标只依赖基金净值序列（A 类指标），不需要个股交易记录。
ANNUAL_RISK_FREE_RATE = 0.02
MAX_PLAUSIBLE_GROSS_EXPOSURE = 1.40
# Published asset buckets are rounded independently.  Allow a small rounding
# margin around the 140% gross-exposure ceiling without accepting materially
# over-limit data.
EXPOSURE_TOLERANCE = 0.001


def _nav_values(nav_series: List[NavPoint]) -> List[float]:
    return [point.nav for point in nav_series if point.nav is not None]


def _slice_trailing_window(nav_series: List[NavPoint], lookback_periods: int) -> List[NavPoint]:
    required_points = lookback_periods + 1
    if len(nav_series) < required_points:
        return []
    return nav_series[-required_points:]


def calculate_period_return(nav_series: List[NavPoint]) -> float:
    values = _nav_values(nav_series)
    if len(values) < 2 or values[0] == 0:
        return 0.0
    return (values[-1] / values[0]) - 1.0


def calculate_max_drawdown(nav_series: List[NavPoint]) -> float:
    values = _nav_values(nav_series)
    if not values:
        return 0.0

    peak = values[0]
    max_drawdown = 0.0
    for value in values:
        if value > peak:
            peak = value
        drawdown = (value / peak) - 1.0
        if drawdown < max_drawdown:
            max_drawdown = drawdown
    return max_drawdown


def calculate_annualized_volatility(nav_series: List[NavPoint]) -> float:
    values = _nav_values(nav_series)
    if len(values) < 2:
        return 0.0

    daily_returns = []
    for previous, current in zip(values[:-1], values[1:]):
        if previous == 0:
            continue
        daily_returns.append((current / previous) - 1.0)

    if not daily_returns:
        return 0.0

    mean_return = sum(daily_returns) / len(daily_returns)
    variance = sum((value - mean_return) ** 2 for value in daily_returns) / len(daily_returns)
    return sqrt(variance) * sqrt(252)


def _daily_returns(nav_series: List[NavPoint]) -> List[float]:
    values = _nav_values(nav_series)
    daily_returns = []
    for previous, current in zip(values[:-1], values[1:]):
        if previous == 0:
            continue
        daily_returns.append((current / previous) - 1.0)
    return daily_returns


def calculate_annualized_return(nav_series: List[NavPoint]) -> float:
    daily_returns = _daily_returns(nav_series)
    if not daily_returns:
        return 0.0
    mean_daily_return = sum(daily_returns) / len(daily_returns)
    return mean_daily_return * TRADING_DAYS_PER_YEAR


def calculate_downside_deviation(nav_series: List[NavPoint], target: float = 0.0) -> float:
    daily_returns = _daily_returns(nav_series)
    if not daily_returns:
        return 0.0
    squared_downside = [min(value - target, 0.0) ** 2 for value in daily_returns]
    mean_squared = sum(squared_downside) / len(squared_downside)
    return sqrt(mean_squared) * sqrt(TRADING_DAYS_PER_YEAR)


def calculate_sharpe_ratio(
    nav_series: List[NavPoint], risk_free_rate: float = ANNUAL_RISK_FREE_RATE
) -> float:
    annualized_volatility = calculate_annualized_volatility(nav_series)
    if annualized_volatility == 0:
        return 0.0
    annualized_return = calculate_annualized_return(nav_series)
    return (annualized_return - risk_free_rate) / annualized_volatility


def calculate_sortino_ratio(
    nav_series: List[NavPoint], risk_free_rate: float = ANNUAL_RISK_FREE_RATE
) -> float:
    downside_deviation = calculate_downside_deviation(nav_series)
    if downside_deviation == 0:
        return 0.0
    annualized_return = calculate_annualized_return(nav_series)
    return (annualized_return - risk_free_rate) / downside_deviation


def calculate_calmar_ratio(nav_series: List[NavPoint]) -> float:
    max_drawdown = calculate_max_drawdown(nav_series)
    if max_drawdown == 0:
        return 0.0
    annualized_return = calculate_annualized_return(nav_series)
    return annualized_return / abs(max_drawdown)


def calculate_positive_period_ratio(nav_series: List[NavPoint]) -> float:
    daily_returns = _daily_returns(nav_series)
    if not daily_returns:
        return 0.0
    positive_periods = len([value for value in daily_returns if value > 0])
    return positive_periods / len(daily_returns)


def calculate_industry_concentration(industry_exposure: Dict[str, float]) -> float:
    if not industry_exposure:
        return 0.0
    return max(industry_exposure.values())


def _holding_weight(row: Dict[str, Any]) -> Optional[float]:
    return holding_weight_fraction(row)


def _normalize_asset_allocation(asset_allocation: Dict[str, float]) -> Dict[str, float]:
    """Read the internal fraction contract without re-guessing numeric units."""

    normalized, _ = _normalize_asset_allocation_with_invalid_count(asset_allocation)
    return normalized


def _normalize_asset_allocation_with_invalid_count(
    asset_allocation: Dict[str, float],
) -> tuple[Dict[str, float], int]:
    """Return canonical allocation plus the number of unusable source values."""

    normalized = {}
    invalid_count = 0
    for key, value in asset_allocation.items():
        weight = canonical_fraction(value)
        if key and weight is not None:
            normalized[str(key)] = weight
        else:
            invalid_count += 1
    return normalized, invalid_count


def _weights_are_plausible(weights: List[float]) -> bool:
    if any(weight < 0 or weight > MAX_PLAUSIBLE_GROSS_EXPOSURE for weight in weights):
        return False
    return sum(weights) <= MAX_PLAUSIBLE_GROSS_EXPOSURE + EXPOSURE_TOLERANCE


def _asset_name_key(name: str) -> str:
    return str(name or "").strip().lower().replace(" ", "").replace("_", "").replace("-", "")


def _asset_bucket_weight(asset_allocation: Dict[str, float], keywords: List[str]) -> float:
    keyword_set = [_asset_name_key(keyword) for keyword in keywords]
    total = 0.0
    for name, weight in asset_allocation.items():
        normalized_name = _asset_name_key(name)
        if any(keyword and keyword in normalized_name for keyword in keyword_set):
            total += weight
    return total


def calculate_bond_exposure_metrics(
    bond_holdings: List[Dict[str, Any]],
    asset_allocation: Dict[str, float],
    invalid_asset_allocation_count: int = 0,
) -> Dict[str, Any]:
    parsed_weights = [_holding_weight(row) for row in bond_holdings]
    weights = sorted([weight for weight in parsed_weights if weight is not None], reverse=True)
    invalid_bond_weight_count = len(parsed_weights) - len(weights)
    asset_weights = list(asset_allocation.values())
    bond_weights_valid = (
        not bond_holdings
        or (
            invalid_bond_weight_count == 0
            and _weights_are_plausible(weights)
        )
    )
    asset_allocation_valid = (
        invalid_asset_allocation_count == 0
        and (not asset_allocation or _weights_are_plausible(asset_weights))
    )
    metrics = {
        "bond_holding_count": float(len(bond_holdings)),
        "asset_allocation_count": float(len(asset_allocation)),
        "bond_top_holding_weight": weights[0] if weights else 0.0,
        "bond_top_three_weight": sum(weights[:3]),
        "bond_total_disclosed_weight": sum(weights),
        "asset_bond_weight": _asset_bucket_weight(asset_allocation, ["债券", "bond", "固定收益", "fixedincome"]),
        "asset_cash_weight": _asset_bucket_weight(asset_allocation, ["现金", "cash", "货币", "money"]),
        "asset_stock_weight": _asset_bucket_weight(asset_allocation, ["股票", "stock", "equity", "权益"]),
        "invalid_bond_weight_count": float(invalid_bond_weight_count),
        "invalid_asset_allocation_count": float(invalid_asset_allocation_count),
        "bond_weights_valid": bond_weights_valid,
        "asset_allocation_valid": asset_allocation_valid,
    }
    allocated_known = (
        metrics["asset_bond_weight"]
        + metrics["asset_cash_weight"]
        + metrics["asset_stock_weight"]
    )
    metrics["asset_other_weight"] = max(0.0, sum(asset_allocation.values()) - allocated_known)
    return metrics


def calculate_excess_return(nav_series: List[NavPoint], benchmark_nav_series: List[NavPoint]) -> float:
    return calculate_period_return(nav_series) - calculate_period_return(benchmark_nav_series)


def calculate_trailing_period_return(nav_series: List[NavPoint], lookback_periods: int) -> Optional[float]:
    window_series = _slice_trailing_window(nav_series, lookback_periods)
    if not window_series:
        return None
    return calculate_period_return(window_series)


def calculate_trailing_max_drawdown(nav_series: List[NavPoint], lookback_periods: int) -> Optional[float]:
    window_series = _slice_trailing_window(nav_series, lookback_periods)
    if not window_series:
        return None
    return calculate_max_drawdown(window_series)


def calculate_trailing_annualized_volatility(nav_series: List[NavPoint], lookback_periods: int) -> Optional[float]:
    window_series = _slice_trailing_window(nav_series, lookback_periods)
    if not window_series:
        return None
    return calculate_annualized_volatility(window_series)


def _build_window_metrics(
    nav_series: List[NavPoint],
    metric_prefix: str,
    calculator: Callable[[List[NavPoint], int], Optional[float]],
) -> Dict[str, float]:
    metrics = {}
    for window_name, lookback_periods in TRADING_WINDOWS.items():
        value = calculator(nav_series, lookback_periods)
        if value is not None:
            metrics[f"{metric_prefix}_{window_name}"] = value
    return metrics


def _append_missing(missing_fields: List[str], field_name: str) -> None:
    if field_name not in missing_fields:
        missing_fields.append(field_name)


class FeatureBuilder:
    """Build stable, testable features before any LLM call."""

    def build(self, payload: FundAnalysisInput) -> FundFeaturePack:
        missing_fields = payload.validate_required_fields()
        fund_type_profile = classify_fund_type(payload.fund_info.category)
        data_coverage = build_data_coverage(payload)

        if not payload.nav_series:
            _append_missing(missing_fields, "nav_series")
        missing_statuses = {MISSING, MISSING_BACKEND_CAPABILITY}
        if data_coverage.get("industry_exposure") in missing_statuses:
            _append_missing(missing_fields, "industry_exposure")
        if data_coverage.get("stock_holdings") in missing_statuses:
            _append_missing(missing_fields, "top_holdings_weight")
        if data_coverage.get("bond_holdings") in missing_statuses:
            _append_missing(missing_fields, "bond_holdings")
        if data_coverage.get("asset_allocation") in missing_statuses:
            _append_missing(missing_fields, "asset_allocation")
        if payload.benchmark and not payload.benchmark_nav_series:
            _append_missing(missing_fields, "benchmark_nav_series")
        normalized_news_summary = list(payload.news_summary)
        if not normalized_news_summary and payload.news_items:
            normalized_news_summary = [
                item.summary or item.title
                for item in payload.news_items
                if item.summary or item.title
            ]

        return_metrics = {
            "total_return": calculate_period_return(payload.nav_series),
            "return_since_inception": calculate_period_return(payload.nav_series),
            "annualized_return": calculate_annualized_return(payload.nav_series),
        }
        return_metrics.update(
            _build_window_metrics(
                payload.nav_series,
                "return",
                calculate_trailing_period_return,
            )
        )

        risk_metrics = {
            "max_drawdown": calculate_max_drawdown(payload.nav_series),
            "annualized_volatility": calculate_annualized_volatility(payload.nav_series),
            "sharpe_ratio": calculate_sharpe_ratio(payload.nav_series),
            "sortino_ratio": calculate_sortino_ratio(payload.nav_series),
            "calmar_ratio": calculate_calmar_ratio(payload.nav_series),
            "positive_period_ratio": calculate_positive_period_ratio(payload.nav_series),
        }
        risk_metrics.update(
            _build_window_metrics(
                payload.nav_series,
                "max_drawdown",
                calculate_trailing_max_drawdown,
            )
        )
        risk_metrics.update(
            _build_window_metrics(
                payload.nav_series,
                "annualized_volatility",
                calculate_trailing_annualized_volatility,
            )
        )

        exposure_metrics = {
            "industry_concentration": calculate_industry_concentration(payload.industry_exposure),
            "top_holdings_weight": float(payload.top_holdings_weight or 0.0),
        }
        asset_allocation, locally_invalid_asset_allocation_count = (
            _normalize_asset_allocation_with_invalid_count(payload.asset_allocation)
        )
        invalid_asset_allocation_count = (
            max(0, int(payload.invalid_asset_allocation_count))
            + locally_invalid_asset_allocation_count
        )
        bond_exposure_metrics = calculate_bond_exposure_metrics(
            payload.bond_holdings,
            asset_allocation,
            invalid_asset_allocation_count=invalid_asset_allocation_count,
        )
        exposure_metrics.update(
            {
                "bond_top_holding_weight": bond_exposure_metrics.get("bond_top_holding_weight", 0.0),
                "bond_top_three_weight": bond_exposure_metrics.get("bond_top_three_weight", 0.0),
                "bond_total_disclosed_weight": bond_exposure_metrics.get("bond_total_disclosed_weight", 0.0),
            }
        )

        benchmark_metrics = {}
        if payload.benchmark_nav_series:
            benchmark_total_return = calculate_period_return(payload.benchmark_nav_series)
            benchmark_metrics = {
                "benchmark_total_return": benchmark_total_return,
                "excess_return": calculate_excess_return(payload.nav_series, payload.benchmark_nav_series),
            }
            benchmark_return_metrics = _build_window_metrics(
                payload.benchmark_nav_series,
                "benchmark_return",
                calculate_trailing_period_return,
            )
            benchmark_metrics.update(benchmark_return_metrics)
            for window_name in TRADING_WINDOWS:
                fund_key = f"return_{window_name}"
                benchmark_key = f"benchmark_return_{window_name}"
                if fund_key in return_metrics and benchmark_key in benchmark_metrics:
                    benchmark_metrics[f"excess_return_{window_name}"] = (
                        return_metrics[fund_key] - benchmark_metrics[benchmark_key]
                    )

        data_quality_metrics = {
            "nav_point_count": len(payload.nav_series),
            "benchmark_nav_point_count": len(payload.benchmark_nav_series),
            "news_item_count": len(payload.news_items),
            "news_signal_count": max(len(payload.news_items), len(normalized_news_summary)),
            "top_holding_count": len(payload.top_holdings),
            "bond_holding_count": len(payload.bond_holdings),
            "asset_allocation_count": len(asset_allocation),
            "invalid_bond_weight_count": int(
                bond_exposure_metrics.get("invalid_bond_weight_count", 0)
            ),
            "invalid_asset_allocation_count": int(
                bond_exposure_metrics.get("invalid_asset_allocation_count", 0)
            ),
            "profit_probability_count": len(payload.profit_probability),
            "individual_analysis_count": len(payload.individual_analysis),
            "available_return_window_count": len(
                [key for key in return_metrics if key.startswith("return_") and key != "return_since_inception"]
            ),
            "available_benchmark_window_count": len(
                [key for key in benchmark_metrics if key.startswith("benchmark_return_")]
            ),
        }

        data_quality_flags = {
            "has_benchmark": bool(payload.benchmark and payload.benchmark_nav_series),
            "has_industry_exposure": bool(payload.industry_exposure),
            "has_top_holdings_weight": payload.top_holdings_weight is not None,
            "has_top_holdings": bool(payload.top_holdings),
            "has_news_signal": bool(normalized_news_summary or payload.news_items),
            "has_structured_news": bool(payload.news_items),
            "has_bond_holdings": bool(payload.bond_holdings),
            # Presence and validity are separate: if every supplied value is
            # invalid, the specialist must report an error rather than silently
            # treating the source as absent.
            "has_asset_allocation": bool(payload.asset_allocation)
            or invalid_asset_allocation_count > 0,
            "bond_holdings_valid": bool(
                bond_exposure_metrics.get("bond_weights_valid", True)
            ),
            "asset_allocation_valid": bool(
                bond_exposure_metrics.get("asset_allocation_valid", True)
            ),
            "has_profit_probability": bool(payload.profit_probability),
            "has_individual_analysis": bool(payload.individual_analysis),
            "fund_type_known": data_coverage.get("fund_type") == AVAILABLE,
            "equity_exposure_applicable": fund_type_profile.equity_exposure_applicable,
            "sector_analysis_applicable": fund_type_profile.sector_analysis_applicable,
            "bond_exposure_applicable": fund_type_profile.bond_exposure_applicable,
            "asset_allocation_required": fund_type_profile.asset_allocation_required,
        }
        for window_name in TRADING_WINDOWS:
            data_quality_flags[f"supports_return_{window_name}"] = f"return_{window_name}" in return_metrics
            data_quality_flags[f"supports_benchmark_return_{window_name}"] = (
                f"benchmark_return_{window_name}" in benchmark_metrics
            )

        return FundFeaturePack(
            request_id=payload.request_id,
            fund_info=payload.fund_info,
            normalized_fund_type=fund_type_profile.normalized_type,
            fund_family=fund_type_profile.family,
            return_metrics=return_metrics,
            risk_metrics=risk_metrics,
            exposure_metrics=exposure_metrics,
            industry_exposure_breakdown=payload.industry_exposure,
            bond_exposure_metrics=bond_exposure_metrics,
            top_holdings=payload.top_holdings,
            bond_holdings=payload.bond_holdings,
            asset_allocation_breakdown=asset_allocation,
            profit_probability=payload.profit_probability,
            individual_analysis=payload.individual_analysis,
            benchmark_metrics=benchmark_metrics,
            data_quality_metrics=data_quality_metrics,
            data_quality_flags=data_quality_flags,
            data_coverage=data_coverage,
            news_summary=normalized_news_summary,
            news_items=payload.news_items,
            missing_fields=missing_fields,
            fund_tags=payload.fund_tags,
            operational_metrics=payload.operational_metrics,
            extra_context=payload.extra_context,
        )
