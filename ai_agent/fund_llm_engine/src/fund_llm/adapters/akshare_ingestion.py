"""One-call ingestion adapter: 基金代码 → FundAnalysisInput.

Centralizes all akshare lookups and Chinese-column-name translation in one
place so backend / notebook callers only need:

    from fund_llm.adapters import build_input_from_code
    payload = build_input_from_code("000001", start_date="2025-01-01", end_date="2025-05-01")
    result = run_real_analysis_for_input(payload)

Each external data source is guarded with `with_*` flags and try/except,
so a slow / failing data source degrades to a skipped agent rather than
blowing up the whole request.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

import akshare as ak

from fund_llm.contracts import (
    AnalysisWindow,
    FundAnalysisInput,
    FundInfo,
    NavPoint,
    NewsItem,
)

_FUND_NAME_CACHE: Optional[List[Dict[str, Any]]] = None


def _load_fund_name_list() -> List[Dict[str, Any]]:
    global _FUND_NAME_CACHE
    if _FUND_NAME_CACHE is None:
        df = ak.fund_name_em()
        _FUND_NAME_CACHE = df.to_dict("records")
    return _FUND_NAME_CACHE


def _lookup_fund_info(code: str, fallback_name: str = "") -> FundInfo:
    try:
        matched = next(
            (item for item in _load_fund_name_list() if str(item.get("基金代码", "")) == code),
            None,
        )
    except Exception:
        matched = None
    return FundInfo(
        code=code,
        name=str((matched or {}).get("基金简称") or fallback_name or code),
        asset_type="fund_open",
        category=str((matched or {}).get("基金类型") or "unknown"),
        manager=None,
    )


def _coerce_iso_date(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()[:10]
    return str(value)[:10]


def _fetch_nav_series(
    code: str,
    start_date: Optional[str],
    end_date: Optional[str],
    max_points: int,
) -> List[NavPoint]:
    df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
    points: List[NavPoint] = []
    for row in df.to_dict("records"):
        point_date = _coerce_iso_date(row.get("净值日期"))
        nav_raw = row.get("单位净值")
        if not point_date or nav_raw is None:
            continue
        if start_date and point_date < start_date:
            continue
        if end_date and point_date > end_date:
            continue
        try:
            nav = float(nav_raw)
        except (TypeError, ValueError):
            continue
        points.append(NavPoint(date=point_date, nav=nav))
    points.sort(key=lambda point: point.date)
    if max_points > 0:
        points = points[-max_points:]
    return points


def _latest_label(values: Any) -> Optional[str]:
    if values is None:
        return None
    cleaned = sorted({str(v) for v in values if v is not None and str(v).strip()})
    return cleaned[-1] if cleaned else None


def _fetch_industry_exposure(code: str, portfolio_year: str) -> Dict[str, float]:
    try:
        df = ak.fund_portfolio_industry_allocation_em(symbol=code, date=portfolio_year)
    except Exception:
        return {}
    if df is None or df.empty:
        return {}
    latest = _latest_label(df.get("截止时间"))
    if latest is None:
        return {}
    rows = df[df["截止时间"] == latest]
    exposure: Dict[str, float] = {}
    for _, row in rows.iterrows():
        name = str(row.get("行业类别") or "").strip()
        pct_raw = row.get("占净值比例")
        if not name or pct_raw is None:
            continue
        try:
            exposure[name] = float(pct_raw)
        except (TypeError, ValueError):
            continue
    return exposure


def _fetch_top_holdings(code: str, portfolio_year: str, top_n: int) -> List[Dict[str, Any]]:
    try:
        df = ak.fund_portfolio_hold_em(symbol=code, date=portfolio_year)
    except Exception:
        return []
    if df is None or df.empty:
        return []
    latest = _latest_label(df.get("季度"))
    if latest is None:
        return []
    rows = df[df["季度"] == latest].sort_values("占净值比例", ascending=False).head(top_n)
    return rows.to_dict("records")


def _sum_holdings_weight(holdings: List[Dict[str, Any]]) -> Optional[float]:
    if not holdings:
        return None
    total = 0.0
    for record in holdings:
        try:
            total += float(record.get("占净值比例") or 0.0)
        except (TypeError, ValueError):
            continue
    return total if total > 0 else None


def _fetch_news_items_for_holdings(
    holdings: List[Dict[str, Any]],
    per_stock: int,
) -> List[NewsItem]:
    items: List[NewsItem] = []
    for record in holdings:
        stock_code = str(record.get("股票代码") or "").strip()
        stock_name = str(record.get("股票名称") or "").strip()
        if not stock_code:
            continue
        try:
            df = ak.stock_news_em(symbol=stock_code)
        except Exception:
            continue
        if df is None or df.empty:
            continue
        if "发布时间" in df.columns:
            df = df.sort_values("发布时间", ascending=False)
        for news_row in df.head(per_stock).to_dict("records"):
            title = str(news_row.get("新闻标题") or "").strip()
            summary = str(news_row.get("新闻内容") or "").strip()[:500]
            if not title and not summary:
                continue
            items.append(
                NewsItem(
                    title=f"[{stock_name}] {title}" if stock_name and title else (title or stock_name),
                    summary=summary,
                    published_at=str(news_row.get("发布时间") or "") or None,
                    source=str(news_row.get("文章来源") or "") or None,
                    topic=stock_name or None,
                    sentiment_label=None,
                )
            )
    return items


def build_input_from_code(
    code: str,
    *,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_nav_points: int = 260,
    portfolio_year: str = "2024",
    top_holdings_n: int = 10,
    with_holdings: bool = True,
    with_industry: bool = True,
    with_news: bool = True,
    news_per_stock: int = 2,
    news_top_stocks: int = 5,
    client_risk_profile: str = "balanced",
    fund_name_fallback: str = "",
) -> FundAnalysisInput:
    """One-call ingestion: fetch all data sources from akshare and assemble a
    ready-to-analyze :class:`FundAnalysisInput`.

    Parameters
    ----------
    code:
        基金代码, e.g. "000001".
    start_date / end_date:
        ISO date strings (YYYY-MM-DD) used to clip the NAV series. Leave None
        to take whatever akshare returns.
    max_nav_points:
        Keep at most the last N points (newest). 0 disables the cap.
    portfolio_year:
        Year passed to akshare for holdings + industry breakdown lookups.
        Defaults to "2024" because EastMoney's quarterly filings settle in
        the year after the report period.
    top_holdings_n:
        Number of top holdings to aggregate into ``top_holdings_weight``.
    with_holdings / with_industry / with_news:
        Toggle individual data sources. Useful when an upstream source is
        slow or known to be down.
    news_per_stock:
        Number of recent news items per top holding (only used when
        ``with_news`` is True).
    news_top_stocks:
        Number of top holdings to scan for news.
    client_risk_profile:
        Forwarded to ``extra_context`` so SectorAgent can use it.
    fund_name_fallback:
        Display name to use if akshare's fund_name_em lookup misses the code.
    """
    fund_info = _lookup_fund_info(code, fallback_name=fund_name_fallback)
    nav_series = _fetch_nav_series(code, start_date, end_date, max_nav_points)
    if not nav_series:
        raise ValueError(f"No NAV data returned for fund code {code!r}.")

    industry_exposure: Dict[str, float] = {}
    if with_industry:
        industry_exposure = _fetch_industry_exposure(code, portfolio_year)

    holdings: List[Dict[str, Any]] = []
    top_holdings_weight: Optional[float] = None
    if with_holdings:
        holdings = _fetch_top_holdings(code, portfolio_year, top_n=top_holdings_n)
        top_holdings_weight = _sum_holdings_weight(holdings)

    news_items: List[NewsItem] = []
    if with_news:
        news_source_holdings = holdings or _fetch_top_holdings(
            code, portfolio_year, top_n=news_top_stocks
        )
        news_items = _fetch_news_items_for_holdings(
            news_source_holdings[:news_top_stocks], per_stock=news_per_stock
        )

    window = AnalysisWindow(
        start_date=nav_series[0].date,
        end_date=nav_series[-1].date,
        as_of_date=nav_series[-1].date,
    )

    return FundAnalysisInput(
        request_id=f"ingestion-{code}-{window.as_of_date}",
        fund_info=fund_info,
        nav_series=nav_series,
        industry_exposure=industry_exposure,
        top_holdings_weight=top_holdings_weight,
        news_items=news_items,
        analysis_window=window,
        fund_tags=["backend-data", "open-fund"],
        extra_context={
            "data_source": "akshare_ingestion",
            "client_risk_profile": client_risk_profile,
            "portfolio_year": portfolio_year,
            "holdings_count": str(len(holdings)),
            "news_count": str(len(news_items)),
        },
    )
