"""HTTP function-registry client for FundMasterAI backends.

The team backends expose their callable HTTP APIs as JSON function definitions
under `/api/*/functions`. This module keeps the LLM engine decoupled from
hard-coded backend URLs while still giving the orchestration layer a reliable,
typed place to execute those tools.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional
from urllib import error, parse, request

from fund_llm.contracts import (
    AnalysisWindow,
    FundAnalysisInput,
    FundInfo,
    FundOperationalMetrics,
    NavPoint,
    NewsItem,
    PortfolioAnalysisInput,
    PortfolioFundData,
    PortfolioPosition,
    _records_from_payload,
)
from fund_llm.fund_routing import classify_fund_type
from fund_llm.ratios import (
    first_present_value,
    holding_weight_fraction,
    normalize_backend_holding,
    percentage_points_to_fraction,
    to_finite_float,
)


JsonDict = Dict[str, Any]
Transport = Callable[[str, str, Optional[JsonDict], int], JsonDict]

# 排障日志：记录 Agent 对后端的每一次 HTTP 调用（目标、耗时、结果）。
# 只做记录，不改变任何请求行为；级别默认 INFO，可通过 logging 配置关闭。
logger = logging.getLogger("fund_llm.backend_calls")


class BackendFunctionError(RuntimeError):
    """Raised when backend function discovery or execution fails."""


@dataclass(frozen=True)
class BackendService:
    name: str
    base_url: str
    functions_path: str


@dataclass(frozen=True)
class RegisteredFunction:
    service: str
    spec: JsonDict

    @property
    def name(self) -> str:
        return str(self.spec.get("name", ""))

    @property
    def path(self) -> str:
        return str(self.spec.get("path", ""))

    @property
    def method(self) -> str:
        return str(self.spec.get("method", "GET")).upper()


def default_services() -> Dict[str, BackendService]:
    return {
        "market": BackendService(
            name="market",
            base_url=os.getenv("MARKET_BACKEND_URL", "http://127.0.0.1:5001"),
            functions_path="/api/market/functions",
        ),
        "news": BackendService(
            name="news",
            base_url=os.getenv("NEWS_BACKEND_URL", "http://127.0.0.1:5000"),
            functions_path="/api/news/functions",
        ),
        "portfolio": BackendService(
            name="portfolio",
            base_url=os.getenv("PORTFOLIO_BACKEND_URL", "http://127.0.0.1:5002"),
            functions_path="/api/portfolio/functions",
        ),
    }


def _join_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _normalize_date(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()[:10]
    text = str(value).strip()
    if not text:
        return ""
    match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", text)
    if match:
        year, month, day = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    match = re.search(r"(\d{4})(\d{2})(\d{2})", text)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month}-{day}"
    try:
        return parsedate_to_datetime(text).date().isoformat()
    except (TypeError, ValueError, IndexError, OverflowError):
        pass
    return text[:10]


def _to_float(value: Any) -> Optional[float]:
    return to_finite_float(value)


def _percent_to_fraction(value: Any) -> Optional[float]:
    return percentage_points_to_fraction(value)


def _aum_to_billion(value: Any) -> Optional[float]:
    number = _to_float(value)
    if number is None:
        return None
    text = str(value)
    if "亿" in text:
        return number / 10.0
    if "万" in text:
        return number / 100000.0
    return number


def _first_record(data: Any) -> JsonDict:
    if isinstance(data, list):
        return data[0] if data and isinstance(data[0], dict) else {}
    return data if isinstance(data, dict) else {}


def _json_preview(data: Any, limit: int = 1200) -> str:
    text = json.dumps(data, ensure_ascii=False, default=str)
    return text[:limit]


class BackendFunctionClient:
    """Discover and call HTTP tools exposed by the team backends."""

    def __init__(
        self,
        services: Optional[Mapping[str, BackendService]] = None,
        timeout_seconds: Optional[int] = None,
        transport: Optional[Transport] = None,
    ):
        self.services = dict(services or default_services())
        if timeout_seconds is None:
            timeout_seconds = int(os.getenv("BACKEND_FUNCTION_TIMEOUT_SECONDS", "75"))
        self.timeout_seconds = timeout_seconds
        self.transport = transport
        self.functions: Dict[str, RegisteredFunction] = {}

    def _request_json(
        self,
        method: str,
        url: str,
        payload: Optional[JsonDict] = None,
        timeout_seconds: Optional[int] = None,
    ) -> JsonDict:
        effective_timeout = timeout_seconds or self.timeout_seconds
        # 调用前先记一笔：就算后端卡死无响应，日志里也能看到"发出去了、在等谁"。
        logger.info("backend call start: %s %s (timeout=%ss)", method.upper(), url, effective_timeout)
        started = time.monotonic()
        try:
            result = self._request_json_inner(method, url, payload, effective_timeout)
        except Exception as exc:
            elapsed = time.monotonic() - started
            logger.warning("backend call FAILED after %.1fs: %s %s -> %s", elapsed, method.upper(), url, exc)
            raise
        elapsed = time.monotonic() - started
        logger.info("backend call ok in %.1fs: %s %s", elapsed, method.upper(), url)
        return result

    def _request_json_inner(
        self,
        method: str,
        url: str,
        payload: Optional[JsonDict] = None,
        timeout_seconds: Optional[int] = None,
    ) -> JsonDict:
        effective_timeout = timeout_seconds or self.timeout_seconds
        if self.transport:
            return self.transport(method.upper(), url, payload, effective_timeout)

        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        http_request = request.Request(url, data=body, headers=headers, method=method.upper())
        try:
            with request.urlopen(http_request, timeout=effective_timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")
            raise BackendFunctionError(f"HTTP {exc.code} from {url}: {response_body[:400]}") from exc
        except error.URLError as exc:
            raise BackendFunctionError(f"Backend request failed for {url}: {exc}") from exc

    def discover(self, service_name: str, tag: Optional[str] = None) -> List[RegisteredFunction]:
        service = self.services[service_name]
        url = _join_url(service.base_url, service.functions_path)
        if tag:
            url = f"{url}?{parse.urlencode({'tag': tag})}"
        payload = self._request_json("GET", url)
        functions = payload.get("data", [])
        if not isinstance(functions, list):
            raise BackendFunctionError(f"Invalid function registry response from {url}.")

        registered: List[RegisteredFunction] = []
        for spec in functions:
            if not isinstance(spec, dict) or not spec.get("name"):
                continue
            item = RegisteredFunction(service=service.name, spec=spec)
            self.functions[item.name] = item
            registered.append(item)
        return registered

    def discover_fund_tools(self, include_portfolio: bool = False) -> Dict[str, RegisteredFunction]:
        # market registry 是必需的（NAV/基本信息都来自它），失败直接抛出；
        # news registry 是可降级项：新闻后端不可用时继续分析，
        # SentimentAgent 会按"无新闻数据"输出 skipped，而不是拖垮整体分析。
        self.discover("market", tag="fund")
        try:
            self.discover("news", tag="fund")
        except BackendFunctionError as exc:
            logger.warning("News registry discovery failed, continuing without news tools: %s", exc)
        if include_portfolio:
            try:
                self.discover("portfolio", tag="holding")
            except BackendFunctionError as exc:
                logger.warning(
                    "Portfolio registry discovery failed, continuing without portfolio tools: %s", exc
                )
        return dict(self.functions)

    def openai_tools(self, names: Optional[Iterable[str]] = None) -> List[JsonDict]:
        selected_names = set(names) if names is not None else set(self.functions)
        tools = []
        for name, item in self.functions.items():
            if name not in selected_names:
                continue
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": item.spec.get("description", ""),
                        "parameters": item.spec.get("parameters", {"type": "object", "properties": {}}),
                    },
                }
            )
        return tools

    def call(
        self,
        name: str,
        arguments: Optional[JsonDict] = None,
        timeout_seconds: Optional[int] = None,
    ) -> Any:
        if name not in self.functions:
            self.discover_fund_tools(include_portfolio=True)
        if name not in self.functions:
            raise BackendFunctionError(f"Backend function {name!r} was not discovered.")

        item = self.functions[name]
        service = self.services[item.service]
        args = dict(arguments or {})
        path = item.path
        for placeholder in re.findall(r"{([^}]+)}", path):
            if placeholder not in args:
                raise BackendFunctionError(f"Missing path parameter {placeholder!r} for {name}.")
            path = path.replace("{" + placeholder + "}", parse.quote(str(args.pop(placeholder))))

        url = _join_url(service.base_url, path)
        method = item.method
        request_payload: Optional[JsonDict] = None
        if method == "GET":
            if args:
                url = f"{url}?{parse.urlencode(args, doseq=True)}"
        else:
            request_payload = args

        effective_timeout = timeout_seconds or self.timeout_seconds
        started_at = time.perf_counter()
        payload_preview = _json_preview(request_payload, limit=600) if request_payload is not None else None
        logger.info(
            "Calling backend function %s via %s %s timeout=%ss payload=%s",
            name,
            method,
            url,
            effective_timeout,
            payload_preview,
        )
        try:
            response_payload = self._request_json(method, url, request_payload, timeout_seconds=effective_timeout)
        except Exception:
            elapsed = time.perf_counter() - started_at
            logger.exception(
                "Backend function %s failed after %.2fs via %s %s payload=%s",
                name,
                elapsed,
                method,
                url,
                payload_preview,
            )
            raise

        elapsed = time.perf_counter() - started_at
        code = response_payload.get("code", 200)
        if code != 200:
            logger.warning(
                "Backend function %s returned code=%s after %.2fs via %s %s",
                name,
                code,
                elapsed,
                method,
                url,
            )
            raise BackendFunctionError(
                f"Backend function {name} returned code={code}: {response_payload.get('message', '')}"
            )
        data = response_payload.get("data")
        records = len(data) if isinstance(data, list) else (1 if data else 0)
        logger.info(
            "Backend function %s succeeded after %.2fs via %s %s records=%s",
            name,
            elapsed,
            method,
            url,
            records,
        )
        return data


def _select_latest_quarter(records: List[JsonDict], quarter_key: str = "quarter") -> List[JsonDict]:
    labels = sorted({str(row.get(quarter_key, "")).strip() for row in records if row.get(quarter_key)})
    if not labels:
        return records
    latest = labels[-1]
    return [row for row in records if str(row.get(quarter_key, "")).strip() == latest]


def _holding_weight(row: JsonDict) -> Optional[float]:
    return holding_weight_fraction(row)


def _build_industry_exposure(records: List[JsonDict]) -> Dict[str, float]:
    exposure: Dict[str, float] = {}
    for row in records:
        name = str(
            row.get("industry_category")
            or row.get("industry")
            or row.get("sector")
            or ""
        ).strip()
        pct = _percent_to_fraction(first_present_value(row, ("pct", "net_value_pct")))
        if name and pct is not None:
            exposure[name] = pct
    return exposure


def _build_asset_allocation_with_invalid_count(
    records: List[JsonDict],
) -> tuple[Dict[str, float], int]:
    allocation: Dict[str, float] = {}
    invalid_count = 0
    for row in records:
        name = str(row.get("asset_type") or row.get("asset_class") or row.get("资产类型") or "").strip()
        pct = _percent_to_fraction(
            first_present_value(row, ("pct", "net_value_pct", "仓位占比"))
        )
        if name and pct is not None:
            allocation[name] = pct
        else:
            invalid_count += 1
    return allocation, invalid_count


def _build_asset_allocation(records: List[JsonDict]) -> Dict[str, float]:
    allocation, _ = _build_asset_allocation_with_invalid_count(records)
    return allocation


def _build_nav_series(
    records: List[JsonDict],
    max_points: int,
    *,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[NavPoint]:
    normalized_start_date = _normalize_date(start_date)
    normalized_end_date = _normalize_date(end_date)
    points: List[NavPoint] = []
    for row in records:
        point_date = _normalize_date(row.get("date") or row.get("净值日期"))
        nav = _to_float(row.get("unit_net_value") or row.get("nav") or row.get("current_unit_net_value"))
        if not point_date or nav is None:
            continue
        if normalized_start_date and point_date < normalized_start_date:
            continue
        if normalized_end_date and point_date > normalized_end_date:
            continue
        points.append(NavPoint(date=point_date, nav=nav))
    points.sort(key=lambda point: point.date)
    if max_points > 0 and not normalized_start_date:
        points = points[-max_points:]
    return points


def _build_news_items(records: List[JsonDict], limit: int) -> List[NewsItem]:
    if limit <= 0:
        return []

    def news_date_key(row: JsonDict) -> str:
        normalized_date = _normalize_date(row.get("announcement_date") or row.get("publish_time"))
        return normalized_date if re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized_date) else ""

    items = []
    for row in sorted(records, key=news_date_key, reverse=True):
        title = str(row.get("announcement_title") or row.get("news_title") or "").strip()
        summary = str(row.get("news_content") or title).strip()
        if not title and not summary:
            continue
        items.append(
            NewsItem(
                title=title,
                summary=summary[:500],
                published_at=_normalize_date(row.get("announcement_date") or row.get("publish_time")) or None,
                source=str(row.get("source") or "public_fund_announcement"),
                topic="fund_announcement",
                sentiment_label=None,
            )
        )
        if len(items) >= limit:
            break
    return items


def build_fund_input_from_backend_functions(
    code: str,
    *,
    client: Optional[BackendFunctionClient] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_nav_points: int = 260,
    portfolio_year: Optional[str] = None,
    top_holdings_n: int = 10,
    max_news_items: int = 8,
    client_risk_profile: str = "balanced",
    fund_name_fallback: str = "",
) -> FundAnalysisInput:
    """Assemble `FundAnalysisInput` using the backend function registry."""

    tool_client = client or BackendFunctionClient()
    tool_client.discover_fund_tools()

    tool_trace: List[JsonDict] = []
    optional_timeout_seconds = int(
        os.getenv("BACKEND_OPTIONAL_FUNCTION_TIMEOUT_SECONDS", str(tool_client.timeout_seconds))
    )

    def safe_call(
        function_name: str,
        args: JsonDict,
        required: bool = False,
        timeout_seconds: Optional[int] = None,
    ) -> Any:
        try:
            data = tool_client.call(function_name, args, timeout_seconds=timeout_seconds)
            size = len(data) if isinstance(data, list) else (1 if data else 0)
            tool_trace.append({"function": function_name, "status": "success", "records": size})
            return data
        except Exception as exc:
            tool_trace.append({"function": function_name, "status": "error", "error": str(exc)[:240]})
            if required:
                raise
            return []

    def latest_call_failed(function_name: str) -> bool:
        return bool(
            tool_trace
            and tool_trace[-1].get("function") == function_name
            and tool_trace[-1].get("status") == "error"
        )

    hist_args = {"platform": "efinance", "symbol": "open_fund", "code": code}
    if start_date:
        hist_args["start_date"] = start_date
    if end_date:
        hist_args["end_date"] = end_date
    nav_records = safe_call("get_fund_hist", hist_args, required=True)
    nav_series = _build_nav_series(
        nav_records or [],
        max_points=max_nav_points,
        start_date=start_date,
        end_date=end_date,
    )
    if not nav_series:
        raise ValueError(f"No NAV data returned by backend for fund code {code!r}.")

    basic_info = _first_record(safe_call("get_fund_individual_basic_info", {"code": code}))
    fund_info = FundInfo(
        code=code,
        name=str(
            basic_info.get("fund_name")
            or basic_info.get("fund_full_name")
            or fund_name_fallback
            or code
        ),
        asset_type="fund_open",
        category=str(basic_info.get("fund_type") or "unknown"),
        manager=basic_info.get("fund_manager"),
    )
    fund_type_profile = classify_fund_type(fund_info.category)

    current_year = datetime.now().year
    candidate_years = [portfolio_year] if portfolio_year else [str(current_year), str(current_year - 1)]
    holding_records: List[JsonDict] = []
    for year in [item for item in candidate_years if item]:
        stock_holdings_tool = (
            "get_fund_portfolio_hold_stock"
            if "get_fund_portfolio_hold_stock" in tool_client.functions
            else "get_fund_portfolio_holds"
        )
        holding_records = safe_call(
            stock_holdings_tool,
            {"code": code, "year": str(year)},
            timeout_seconds=optional_timeout_seconds,
        )
        if holding_records:
            portfolio_year = str(year)
            break
        if latest_call_failed(stock_holdings_tool):
            break

    latest_holdings = [
        normalize_backend_holding(row)
        for row in _select_latest_quarter(holding_records or [])
    ]
    ranked_holdings = sorted(
        latest_holdings,
        key=lambda row: _holding_weight(row) or 0.0,
        reverse=True,
    )
    top_holdings = ranked_holdings[:top_holdings_n]
    top_holdings_weight_values = [
        _holding_weight(row) for row in top_holdings
    ]
    top_holdings_weight = sum(value for value in top_holdings_weight_values if value is not None)
    if top_holdings_weight <= 0:
        top_holdings_weight = None

    industry_records: List[JsonDict] = []
    industry_exposure: Dict[str, float] = {}
    if "get_fund_portfolio_industry_allocation" in tool_client.functions:
        for year in [item for item in candidate_years if item]:
            industry_records = safe_call(
                "get_fund_portfolio_industry_allocation",
                {"code": code, "year": str(year)},
                timeout_seconds=optional_timeout_seconds,
            )
            industry_exposure = _build_industry_exposure(industry_records or [])
            if industry_exposure:
                break
            if latest_call_failed("get_fund_portfolio_industry_allocation"):
                break

    bond_holding_records: List[JsonDict] = []
    if "get_fund_portfolio_hold_bond" in tool_client.functions:
        for year in [item for item in candidate_years if item]:
            bond_holding_records = safe_call(
                "get_fund_portfolio_hold_bond",
                {"code": code, "year": str(year)},
                timeout_seconds=optional_timeout_seconds,
            )
            if bond_holding_records:
                break
            if latest_call_failed("get_fund_portfolio_hold_bond"):
                break
    latest_bond_holdings = sorted(
        [
            normalize_backend_holding(row)
            for row in _select_latest_quarter(bond_holding_records or [])
        ],
        key=lambda row: _holding_weight(row) or 0.0,
        reverse=True,
    )

    asset_allocation_records: List[JsonDict] = []
    if "get_fund_individual_detail_hold" in tool_client.functions:
        asset_allocation_records = safe_call(
            "get_fund_individual_detail_hold",
            {"code": code},
            timeout_seconds=optional_timeout_seconds,
        )
    asset_allocation, invalid_asset_allocation_count = (
        _build_asset_allocation_with_invalid_count(asset_allocation_records or [])
    )

    announcement_records = safe_call(
        "get_public_fund_announcement",
        {"code": code},
        timeout_seconds=optional_timeout_seconds,
    )
    news_items = _build_news_items(announcement_records or [], limit=max_news_items)
    individual_analysis = safe_call(
        "get_fund_individual_analysis",
        {"code": code},
        timeout_seconds=optional_timeout_seconds,
    )
    profit_probability = safe_call(
        "get_fund_profit_probability",
        {"code": code},
        timeout_seconds=optional_timeout_seconds,
    )

    window = AnalysisWindow(
        start_date=nav_series[0].date,
        end_date=nav_series[-1].date,
        as_of_date=nav_series[-1].date,
    )
    operational_metrics = FundOperationalMetrics(
        fund_size_billion=_aum_to_billion(basic_info.get("latest_aum")),
        inception_date=_normalize_date(basic_info.get("inception_date")) or None,
        manager_tenure_years=None,
    )

    successful_tools = [item["function"] for item in tool_trace if item["status"] == "success"]
    errored_tools = [item["function"] for item in tool_trace if item["status"] == "error"]

    fund_tags = [
        "backend-function-registry",
        "open-fund",
        fund_type_profile.normalized_type,
    ]
    if fund_type_profile.family not in {"unknown", fund_type_profile.normalized_type}:
        fund_tags.append(fund_type_profile.family)

    return FundAnalysisInput(
        request_id=f"backend-tools-{code}-{window.as_of_date}",
        fund_info=fund_info,
        nav_series=nav_series,
        industry_exposure=industry_exposure,
        top_holdings_weight=top_holdings_weight,
        top_holdings=[dict(row) for row in top_holdings],
        bond_holdings=latest_bond_holdings,
        asset_allocation=asset_allocation,
        invalid_asset_allocation_count=invalid_asset_allocation_count,
        profit_probability=_records_from_payload(profit_probability),
        individual_analysis=_records_from_payload(individual_analysis),
        news_items=news_items,
        analysis_window=window,
        fund_tags=fund_tags,
        operational_metrics=operational_metrics,
        extra_context={
            "data_source": "backend_function_registry",
            "client_risk_profile": client_risk_profile,
            "raw_fund_type": fund_type_profile.raw_type,
            "normalized_fund_type": fund_type_profile.normalized_type,
            "fund_family": fund_type_profile.family,
            "portfolio_year": str(portfolio_year or ""),
            "holdings_count": str(len(top_holdings)),
            "industry_exposure_count": str(len(industry_exposure)),
            "bond_holdings_count": str(len(latest_bond_holdings)),
            "asset_allocation_count": str(len(asset_allocation_records or [])),
            "invalid_asset_allocation_count": str(invalid_asset_allocation_count),
            "news_count": str(len(news_items)),
            "available_backend_tools": ",".join(sorted(tool_client.functions)),
            "successful_backend_tools": ",".join(successful_tools),
            "errored_backend_tools": ",".join(errored_tools),
            "tool_trace": _json_preview(tool_trace),
            "top_holdings": _json_preview(top_holdings),
            "backend_industry_exposure": _json_preview(industry_records),
            "backend_bond_holdings": _json_preview(latest_bond_holdings),
            "backend_asset_allocation": _json_preview(asset_allocation_records),
            "backend_individual_analysis": _json_preview(individual_analysis),
            "backend_profit_probability": _json_preview(profit_probability),
        },
    )


def build_portfolio_input_from_backend_functions(
    positions: List[PortfolioPosition],
    *,
    client: Optional[BackendFunctionClient] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_nav_points: int = 520,
    client_risk_profile: str = "balanced",
    include_lookthrough: bool = True,
    top_holdings_n: int = 10,
) -> PortfolioAnalysisInput:
    """Assemble `PortfolioAnalysisInput` with a per-fund backend fetch.

    必需数据只有 NAV：任何一只基金 NAV 拉取失败都会抛出 ValueError
    （由 HTTP 层转成 422），不静默丢弃成分基金。

    基本信息和穿透数据（股票持仓 / 行业配置 / 资产配置）是可选降级项：
    某只基金缺某类数据时记入 tool_trace 并继续，由穿透计算输出
    partial / missing 状态，而不是让整个组合分析失败。

    `positions` 权重必须已经归一化（见 `portfolio_analysis.normalize_positions`）。
    """
    from fund_llm.portfolio_analysis import intersect_nav_dates, normalize_positions

    normalized_positions, weights_rescaled = normalize_positions(positions)
    requested_weight_by_code = {position.code: position.weight for position in positions}

    tool_client = client or BackendFunctionClient()
    tool_client.discover_fund_tools()

    optional_timeout_seconds = int(
        os.getenv("BACKEND_OPTIONAL_FUNCTION_TIMEOUT_SECONDS", str(tool_client.timeout_seconds))
    )
    current_year = datetime.now().year
    candidate_years = [str(current_year), str(current_year - 1)]

    tool_trace: List[JsonDict] = []
    funds: List[PortfolioFundData] = []
    failed_codes: List[str] = []

    def optional_call(function_name: str, args: JsonDict, fund_code: str) -> Any:
        """可选工具调用：失败记 trace 返回空，不打断组合分析。"""
        try:
            data = tool_client.call(function_name, args, timeout_seconds=optional_timeout_seconds)
            size = len(data) if isinstance(data, list) else (1 if data else 0)
            tool_trace.append(
                {"function": function_name, "fund_code": fund_code, "status": "success", "records": size}
            )
            return data
        except Exception as exc:
            tool_trace.append(
                {
                    "function": function_name,
                    "fund_code": fund_code,
                    "status": "error",
                    "error": str(exc)[:240],
                }
            )
            return []

    def fetch_top_holdings(fund_code: str) -> List[JsonDict]:
        stock_holdings_tool = (
            "get_fund_portfolio_hold_stock"
            if "get_fund_portfolio_hold_stock" in tool_client.functions
            else "get_fund_portfolio_holds"
        )
        if stock_holdings_tool not in tool_client.functions:
            return []
        for year in candidate_years:
            records = optional_call(stock_holdings_tool, {"code": fund_code, "year": year}, fund_code)
            if records:
                latest = [
                    normalize_backend_holding(row)
                    for row in _select_latest_quarter(records)
                ]
                ranked = sorted(latest, key=lambda row: _holding_weight(row) or 0.0, reverse=True)
                return [dict(row) for row in ranked[:top_holdings_n]]
            if tool_trace and tool_trace[-1].get("status") == "error":
                break
        return []

    def fetch_industry_exposure(fund_code: str) -> Dict[str, float]:
        if "get_fund_portfolio_industry_allocation" not in tool_client.functions:
            return {}
        for year in candidate_years:
            records = optional_call(
                "get_fund_portfolio_industry_allocation", {"code": fund_code, "year": year}, fund_code
            )
            exposure = _build_industry_exposure(records or [])
            if exposure:
                return exposure
            if tool_trace and tool_trace[-1].get("status") == "error":
                break
        return {}

    def fetch_asset_allocation(fund_code: str) -> Dict[str, float]:
        if "get_fund_individual_detail_hold" not in tool_client.functions:
            return {}
        records = optional_call("get_fund_individual_detail_hold", {"code": fund_code}, fund_code)
        return _build_asset_allocation(records or [])

    for position in normalized_positions:
        hist_args = {"platform": "efinance", "symbol": "open_fund", "code": position.code}
        if start_date:
            hist_args["start_date"] = start_date
        if end_date:
            hist_args["end_date"] = end_date

        try:
            nav_records = tool_client.call("get_fund_hist", hist_args)
            tool_trace.append(
                {
                    "function": "get_fund_hist",
                    "fund_code": position.code,
                    "status": "success",
                    "records": len(nav_records) if isinstance(nav_records, list) else 0,
                }
            )
        except Exception as exc:
            tool_trace.append(
                {
                    "function": "get_fund_hist",
                    "fund_code": position.code,
                    "status": "error",
                    "error": str(exc)[:240],
                }
            )
            failed_codes.append(position.code)
            continue

        nav_series = _build_nav_series(
            nav_records or [],
            max_points=max_nav_points,
            start_date=start_date,
            end_date=end_date,
        )
        if not nav_series:
            failed_codes.append(position.code)
            continue

        basic_info: JsonDict = {}
        try:
            basic_info = _first_record(
                tool_client.call("get_fund_individual_basic_info", {"code": position.code})
            )
            tool_trace.append(
                {
                    "function": "get_fund_individual_basic_info",
                    "fund_code": position.code,
                    "status": "success",
                    "records": 1 if basic_info else 0,
                }
            )
        except Exception as exc:
            # 基本信息是可选降级项：缺了只影响名称/类型展示，不影响组合净值合成。
            tool_trace.append(
                {
                    "function": "get_fund_individual_basic_info",
                    "fund_code": position.code,
                    "status": "error",
                    "error": str(exc)[:240],
                }
            )

        fund_info = FundInfo(
            code=position.code,
            name=str(
                basic_info.get("fund_name")
                or basic_info.get("fund_full_name")
                or position.name
                or position.code
            ),
            asset_type="fund_open",
            category=str(basic_info.get("fund_type") or "unknown"),
            manager=basic_info.get("fund_manager"),
        )

        top_holdings: List[JsonDict] = []
        industry_exposure: Dict[str, float] = {}
        asset_allocation: Dict[str, float] = {}
        if include_lookthrough:
            top_holdings = fetch_top_holdings(position.code)
            industry_exposure = fetch_industry_exposure(position.code)
            asset_allocation = fetch_asset_allocation(position.code)

        funds.append(
            PortfolioFundData(
                fund_info=fund_info,
                nav_series=nav_series,
                weight=position.weight,
                requested_weight=requested_weight_by_code.get(position.code, position.weight),
                top_holdings=top_holdings,
                industry_exposure=industry_exposure,
                asset_allocation=asset_allocation,
            )
        )

    if failed_codes:
        raise ValueError(
            "No NAV data returned by backend for fund code(s): "
            f"{', '.join(sorted(failed_codes))}. Portfolio analysis needs NAV history "
            "for every constituent fund."
        )

    # 窗口口径与组合指标一致：用共同日期交集，而不是所有基金日期的并集。
    # 交集为空时留空，由管线的最小重叠检查给出结构化 422，不在这里报错。
    shared_dates = intersect_nav_dates(funds)
    window = AnalysisWindow(
        start_date=shared_dates[0] if shared_dates else None,
        end_date=shared_dates[-1] if shared_dates else None,
        as_of_date=shared_dates[-1] if shared_dates else None,
    )
    successful_tools = sorted(
        {item["function"] for item in tool_trace if item["status"] == "success"}
    )
    errored_tools = sorted(
        {item["function"] for item in tool_trace if item["status"] == "error"}
    )

    return PortfolioAnalysisInput(
        request_id=(
            f"backend-portfolio-{'-'.join(fund.fund_info.code for fund in funds)}"
            f"-{window.as_of_date or 'no-shared-window'}"
        ),
        funds=funds,
        analysis_window=window,
        client_risk_profile=client_risk_profile,
        extra_context={
            "data_source": "backend_function_registry",
            "client_risk_profile": client_risk_profile,
            "weights_rescaled": str(weights_rescaled).lower(),
            "fund_count": str(len(funds)),
            "lookthrough_enabled": str(include_lookthrough).lower(),
            "available_backend_tools": ",".join(sorted(tool_client.functions)),
            "successful_backend_tools": ",".join(successful_tools),
            "errored_backend_tools": ",".join(errored_tools),
            "tool_trace": _json_preview(tool_trace),
        },
    )


def build_sector_view_funds_from_backend_functions(
    codes: List[str],
    *,
    client: Optional[BackendFunctionClient] = None,
) -> tuple:
    """Fetch per-fund basic info and industry allocation for the sector view.

    行业层视图不需要 NAV：每只基金只调基本信息（判断基金类型）和行业配置。
    两类数据都是可降级项：基本信息失败按 unknown 类型处理，行业配置缺失
    由 sector_view 输出 insufficient_data / not_applicable 状态。

    Returns `(funds, context)`：funds 是 `sector_view.SectorViewFund` 列表，
    context 携带 tool_trace 等排障信息。
    """
    from fund_llm.sector_view import SectorViewFund

    normalized_codes = []
    for code in codes:
        text = str(code or "").strip()
        if not text:
            raise ValueError("Every sector-view item needs a fund code.")
        if text in normalized_codes:
            raise ValueError(f"Fund code {text!r} appears more than once in the sector view request.")
        normalized_codes.append(text)
    if not normalized_codes:
        raise ValueError("codes is required. Provide a list of fund codes.")

    tool_client = client or BackendFunctionClient()
    tool_client.discover_fund_tools()

    optional_timeout_seconds = int(
        os.getenv("BACKEND_OPTIONAL_FUNCTION_TIMEOUT_SECONDS", str(tool_client.timeout_seconds))
    )
    current_year = datetime.now().year
    candidate_years = [str(current_year), str(current_year - 1)]
    tool_trace: List[JsonDict] = []

    def optional_call(function_name: str, args: JsonDict, fund_code: str) -> Any:
        try:
            data = tool_client.call(function_name, args, timeout_seconds=optional_timeout_seconds)
            size = len(data) if isinstance(data, list) else (1 if data else 0)
            tool_trace.append(
                {"function": function_name, "fund_code": fund_code, "status": "success", "records": size}
            )
            return data
        except Exception as exc:
            tool_trace.append(
                {
                    "function": function_name,
                    "fund_code": fund_code,
                    "status": "error",
                    "error": str(exc)[:240],
                }
            )
            return []

    funds: List[SectorViewFund] = []
    for code in normalized_codes:
        basic_info = _first_record(
            optional_call("get_fund_individual_basic_info", {"code": code}, code)
        )
        fund_info = FundInfo(
            code=code,
            name=str(basic_info.get("fund_name") or basic_info.get("fund_full_name") or code),
            asset_type="fund_open",
            category=str(basic_info.get("fund_type") or "unknown"),
            manager=basic_info.get("fund_manager"),
        )

        industry_exposure: Dict[str, float] = {}
        if "get_fund_portfolio_industry_allocation" in tool_client.functions:
            for year in candidate_years:
                records = optional_call(
                    "get_fund_portfolio_industry_allocation", {"code": code, "year": year}, code
                )
                industry_exposure = _build_industry_exposure(records or [])
                if industry_exposure:
                    break
                if tool_trace and tool_trace[-1].get("status") == "error":
                    break

        funds.append(SectorViewFund(fund_info=fund_info, industry_exposure=industry_exposure))

    successful_tools = sorted(
        {item["function"] for item in tool_trace if item["status"] == "success"}
    )
    errored_tools = sorted(
        {item["function"] for item in tool_trace if item["status"] == "error"}
    )
    context = {
        "data_source": "backend_function_registry",
        "available_backend_tools": ",".join(sorted(tool_client.functions)),
        "successful_backend_tools": ",".join(successful_tools),
        "errored_backend_tools": ",".join(errored_tools),
        "tool_trace": tool_trace,
    }
    return funds, context
