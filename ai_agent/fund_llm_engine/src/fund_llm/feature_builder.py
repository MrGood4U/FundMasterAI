from math import sqrt
from typing import Callable, Dict, List, Optional

from fund_llm.contracts import FundAnalysisInput, FundFeaturePack, NavPoint

TRADING_WINDOWS = {
    "1m": 21,
    "3m": 63,
    "6m": 126,
    "1y": 252,
}


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


def calculate_industry_concentration(industry_exposure: Dict[str, float]) -> float:
    if not industry_exposure:
        return 0.0
    return max(industry_exposure.values())


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

        if not payload.nav_series:
            _append_missing(missing_fields, "nav_series")
        if not payload.industry_exposure:
            _append_missing(missing_fields, "industry_exposure")
        if payload.top_holdings_weight is None:
            _append_missing(missing_fields, "top_holdings_weight")
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
            "has_news_signal": bool(normalized_news_summary or payload.news_items),
            "has_structured_news": bool(payload.news_items),
        }
        for window_name in TRADING_WINDOWS:
            data_quality_flags[f"supports_return_{window_name}"] = f"return_{window_name}" in return_metrics
            data_quality_flags[f"supports_benchmark_return_{window_name}"] = (
                f"benchmark_return_{window_name}" in benchmark_metrics
            )

        return FundFeaturePack(
            request_id=payload.request_id,
            fund_info=payload.fund_info,
            return_metrics=return_metrics,
            risk_metrics=risk_metrics,
            exposure_metrics=exposure_metrics,
            industry_exposure_breakdown=payload.industry_exposure,
            benchmark_metrics=benchmark_metrics,
            data_quality_metrics=data_quality_metrics,
            data_quality_flags=data_quality_flags,
            news_summary=normalized_news_summary,
            news_items=payload.news_items,
            missing_fields=missing_fields,
            fund_tags=payload.fund_tags,
            operational_metrics=payload.operational_metrics,
            extra_context=payload.extra_context,
        )
