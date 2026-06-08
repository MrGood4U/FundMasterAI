"""HTTP function-registry client for FundMasterAI backends.

The team backends expose their callable HTTP APIs as JSON function definitions
under `/api/*/functions`. This module keeps the LLM engine decoupled from
hard-coded backend URLs while still giving the orchestration layer a reliable,
typed place to execute those tools.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional
from urllib import error, parse, request

from fund_llm.contracts import (
    AnalysisWindow,
    FundAnalysisInput,
    FundInfo,
    FundOperationalMetrics,
    NavPoint,
    NewsItem,
)
from fund_llm.fund_routing import classify_fund_type


JsonDict = Dict[str, Any]
Transport = Callable[[str, str, Optional[JsonDict], int], JsonDict]


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
    return text[:10]


def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    return float(match.group(0))


def _percent_to_fraction(value: Any) -> Optional[float]:
    number = _to_float(value)
    if number is None:
        return None
    return number / 100.0


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

    def _request_json(self, method: str, url: str, payload: Optional[JsonDict] = None) -> JsonDict:
        if self.transport:
            return self.transport(method.upper(), url, payload, self.timeout_seconds)

        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        http_request = request.Request(url, data=body, headers=headers, method=method.upper())
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
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
        self.discover("market", tag="fund")
        self.discover("news", tag="fund")
        if include_portfolio:
            self.discover("portfolio", tag="holding")
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

    def call(self, name: str, arguments: Optional[JsonDict] = None) -> Any:
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

        response_payload = self._request_json(method, url, request_payload)
        code = response_payload.get("code", 200)
        if code != 200:
            raise BackendFunctionError(
                f"Backend function {name} returned code={code}: {response_payload.get('message', '')}"
            )
        return response_payload.get("data")


def _select_latest_quarter(records: List[JsonDict], quarter_key: str = "quarter") -> List[JsonDict]:
    labels = sorted({str(row.get(quarter_key, "")).strip() for row in records if row.get(quarter_key)})
    if not labels:
        return records
    latest = labels[-1]
    return [row for row in records if str(row.get(quarter_key, "")).strip() == latest]


def _holding_weight(row: JsonDict) -> Optional[float]:
    return _percent_to_fraction(row.get("net_value_pct") or row.get("pct"))


def _build_industry_exposure(records: List[JsonDict]) -> Dict[str, float]:
    exposure: Dict[str, float] = {}
    for row in records:
        name = str(
            row.get("industry_category")
            or row.get("industry")
            or row.get("sector")
            or ""
        ).strip()
        pct = _percent_to_fraction(row.get("pct") or row.get("net_value_pct"))
        if name and pct is not None:
            exposure[name] = pct
    return exposure


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
    items = []
    for row in records[:limit]:
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

    def safe_call(function_name: str, args: JsonDict, required: bool = False) -> Any:
        try:
            data = tool_client.call(function_name, args)
            size = len(data) if isinstance(data, list) else (1 if data else 0)
            tool_trace.append({"function": function_name, "status": "success", "records": size})
            return data
        except Exception as exc:
            tool_trace.append({"function": function_name, "status": "error", "error": str(exc)[:240]})
            if required:
                raise
            return []

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
        holding_records = safe_call(stock_holdings_tool, {"code": code, "year": str(year)})
        if holding_records:
            portfolio_year = str(year)
            break

    latest_holdings = _select_latest_quarter(holding_records or [])
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
            )
            industry_exposure = _build_industry_exposure(industry_records or [])
            if industry_exposure:
                break

    bond_holding_records: List[JsonDict] = []
    if "get_fund_portfolio_hold_bond" in tool_client.functions:
        for year in [item for item in candidate_years if item]:
            bond_holding_records = safe_call("get_fund_portfolio_hold_bond", {"code": code, "year": str(year)})
            if bond_holding_records:
                break

    asset_allocation_records: List[JsonDict] = []
    if "get_fund_individual_detail_hold" in tool_client.functions:
        asset_allocation_records = safe_call("get_fund_individual_detail_hold", {"code": code})

    announcement_records = safe_call("get_public_fund_announcement", {"code": code})
    news_items = _build_news_items(announcement_records or [], limit=max_news_items)
    individual_analysis = safe_call("get_fund_individual_analysis", {"code": code})
    profit_probability = safe_call("get_fund_profit_probability", {"code": code})

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
            "bond_holdings_count": str(len(bond_holding_records)),
            "asset_allocation_count": str(len(asset_allocation_records)),
            "news_count": str(len(news_items)),
            "available_backend_tools": ",".join(sorted(tool_client.functions)),
            "successful_backend_tools": ",".join(successful_tools),
            "errored_backend_tools": ",".join(errored_tools),
            "tool_trace": _json_preview(tool_trace),
            "top_holdings": _json_preview(top_holdings),
            "backend_industry_exposure": _json_preview(industry_records),
            "backend_bond_holdings": _json_preview(bond_holding_records),
            "backend_asset_allocation": _json_preview(asset_allocation_records),
            "backend_individual_analysis": _json_preview(individual_analysis),
            "backend_profit_probability": _json_preview(profit_probability),
        },
    )
