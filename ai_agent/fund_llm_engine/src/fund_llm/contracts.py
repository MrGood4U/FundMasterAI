import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


def _coerce_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    return float(match.group(0))


def _coerce_fraction(value: Any) -> Optional[float]:
    number = _coerce_float(value)
    if number is None:
        return None
    if (isinstance(value, str) and "%" in value) or abs(number) > 1.0:
        return number / 100.0
    return number


def _dicts_from_list(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _fraction_dict_from_payload(value: Any) -> Dict[str, float]:
    if not isinstance(value, dict):
        return {}
    normalized = {}
    for key, raw_value in value.items():
        number = _coerce_fraction(raw_value)
        if number is not None:
            normalized[str(key)] = number
    return normalized


@dataclass
class FundInfo:
    code: str
    name: str
    asset_type: str
    category: str = "unknown"
    manager: Optional[str] = None

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "FundInfo":
        payload = payload or {}
        return cls(
            code=str(payload.get("code", "")),
            name=str(payload.get("name", "")),
            asset_type=str(payload.get("asset_type", "")),
            category=str(payload.get("category", "unknown")),
            manager=payload.get("manager"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NavPoint:
    date: str
    nav: float

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "NavPoint":
        return cls(
            date=str(payload.get("date", "")),
            nav=float(payload.get("nav", 0.0)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AnalysisWindow:
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    as_of_date: Optional[str] = None

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "AnalysisWindow":
        payload = payload or {}
        return cls(
            start_date=payload.get("start_date"),
            end_date=payload.get("end_date"),
            as_of_date=payload.get("as_of_date"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BenchmarkInfo:
    code: str
    name: str
    asset_type: str = "index"

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "BenchmarkInfo":
        payload = payload or {}
        return cls(
            code=str(payload.get("code", "")),
            name=str(payload.get("name", "")),
            asset_type=str(payload.get("asset_type", "index")),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FundOperationalMetrics:
    fund_size_billion: Optional[float] = None
    inception_date: Optional[str] = None
    manager_tenure_years: Optional[float] = None

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "FundOperationalMetrics":
        payload = payload or {}
        return cls(
            fund_size_billion=_coerce_float(payload.get("fund_size_billion")),
            inception_date=payload.get("inception_date"),
            manager_tenure_years=_coerce_float(payload.get("manager_tenure_years")),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NewsItem:
    title: str = ""
    summary: str = ""
    published_at: Optional[str] = None
    source: Optional[str] = None
    topic: Optional[str] = None
    sentiment_label: Optional[str] = None

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "NewsItem":
        payload = payload or {}
        return cls(
            title=str(payload.get("title", "")),
            summary=str(payload.get("summary", "")),
            published_at=payload.get("published_at"),
            source=payload.get("source"),
            topic=payload.get("topic"),
            sentiment_label=payload.get("sentiment_label"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FundAnalysisInput:
    request_id: str
    fund_info: FundInfo
    nav_series: List[NavPoint]
    industry_exposure: Dict[str, float] = field(default_factory=dict)
    top_holdings_weight: Optional[float] = None
    bond_holdings: List[Dict[str, Any]] = field(default_factory=list)
    asset_allocation: Dict[str, float] = field(default_factory=dict)
    news_summary: List[str] = field(default_factory=list)
    news_items: List[NewsItem] = field(default_factory=list)
    analysis_window: Optional[AnalysisWindow] = None
    benchmark: Optional[BenchmarkInfo] = None
    benchmark_nav_series: List[NavPoint] = field(default_factory=list)
    fund_tags: List[str] = field(default_factory=list)
    operational_metrics: FundOperationalMetrics = field(default_factory=FundOperationalMetrics)
    extra_context: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "FundAnalysisInput":
        payload = payload or {}
        return cls(
            request_id=str(payload.get("request_id", "")),
            fund_info=FundInfo.from_dict(payload.get("fund_info", {})),
            nav_series=[NavPoint.from_dict(item) for item in payload.get("nav_series", [])],
            industry_exposure={
                str(key): float(value)
                for key, value in (payload.get("industry_exposure") or {}).items()
            },
            top_holdings_weight=_coerce_float(payload.get("top_holdings_weight")),
            bond_holdings=_dicts_from_list(payload.get("bond_holdings")),
            asset_allocation=_fraction_dict_from_payload(payload.get("asset_allocation")),
            news_summary=[str(item) for item in payload.get("news_summary", [])],
            news_items=[NewsItem.from_dict(item) for item in payload.get("news_items", [])],
            analysis_window=AnalysisWindow.from_dict(payload["analysis_window"])
            if payload.get("analysis_window")
            else None,
            benchmark=BenchmarkInfo.from_dict(payload["benchmark"]) if payload.get("benchmark") else None,
            benchmark_nav_series=[NavPoint.from_dict(item) for item in payload.get("benchmark_nav_series", [])],
            fund_tags=[str(item) for item in payload.get("fund_tags", [])],
            operational_metrics=FundOperationalMetrics.from_dict(payload.get("operational_metrics", {})),
            extra_context={
                str(key): str(value)
                for key, value in (payload.get("extra_context") or {}).items()
            },
        )

    def validate_required_fields(self) -> List[str]:
        missing_fields = []
        if not self.request_id:
            missing_fields.append("request_id")
        if not self.fund_info.code:
            missing_fields.append("fund_info.code")
        if not self.fund_info.name:
            missing_fields.append("fund_info.name")
        if not self.fund_info.asset_type:
            missing_fields.append("fund_info.asset_type")
        if not self.nav_series:
            missing_fields.append("nav_series")
        return missing_fields

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FundFeaturePack:
    request_id: str
    fund_info: FundInfo
    normalized_fund_type: str
    fund_family: str
    return_metrics: Dict[str, float]
    risk_metrics: Dict[str, float]
    exposure_metrics: Dict[str, float]
    industry_exposure_breakdown: Dict[str, float] = field(default_factory=dict)
    bond_exposure_metrics: Dict[str, float] = field(default_factory=dict)
    bond_holdings: List[Dict[str, Any]] = field(default_factory=list)
    asset_allocation_breakdown: Dict[str, float] = field(default_factory=dict)
    benchmark_metrics: Dict[str, float] = field(default_factory=dict)
    data_quality_metrics: Dict[str, int] = field(default_factory=dict)
    data_quality_flags: Dict[str, bool] = field(default_factory=dict)
    data_coverage: Dict[str, str] = field(default_factory=dict)
    news_summary: List[str] = field(default_factory=list)
    news_items: List[NewsItem] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    fund_tags: List[str] = field(default_factory=list)
    operational_metrics: FundOperationalMetrics = field(default_factory=FundOperationalMetrics)
    extra_context: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AgentOutput:
    agent_name: str
    status: str
    score: Optional[float]
    stance: str
    key_points: List[str]
    risks: List[str]
    recommendations: List[str]
    confidence: float
    narrative: str

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "AgentOutput":
        payload = payload or {}
        score = payload.get("score")
        return cls(
            agent_name=str(payload.get("agent_name", "")),
            status=str(payload.get("status", "")),
            score=float(score) if score is not None else None,
            stance=str(payload.get("stance", "")),
            key_points=[str(item) for item in payload.get("key_points", [])],
            risks=[str(item) for item in payload.get("risks", [])],
            recommendations=[str(item) for item in payload.get("recommendations", [])],
            confidence=float(payload.get("confidence", 0.0)),
            narrative=str(payload.get("narrative", "")),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AnalysisTraceEvent:
    category: str
    title: str
    detail: str
    status: str = "success"
    evidence: Dict[str, Any] = field(default_factory=dict)
    technical: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "AnalysisTraceEvent":
        payload = payload or {}
        return cls(
            category=str(payload.get("category", "")),
            title=str(payload.get("title", "")),
            detail=str(payload.get("detail", "")),
            status=str(payload.get("status", "success")),
            evidence=dict(payload.get("evidence") or {}),
            technical=dict(payload.get("technical") or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PortfolioPosition:
    """One user-requested portfolio constituent: fund code plus target weight."""

    code: str
    weight: float
    name: str = ""

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "PortfolioPosition":
        payload = payload or {}
        return cls(
            code=str(payload.get("code") or payload.get("fund_code") or "").strip(),
            weight=float(_coerce_float(payload.get("weight")) or 0.0),
            name=str(payload.get("name") or payload.get("fund_name") or "").strip(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PortfolioFundData:
    """Fetched per-fund data used for portfolio NAV composition.

    `weight` is the normalized weight actually used in composition;
    `requested_weight` keeps the raw user input for traceability.
    """

    fund_info: FundInfo
    nav_series: List[NavPoint]
    weight: float
    requested_weight: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PortfolioAnalysisInput:
    request_id: str
    funds: List[PortfolioFundData]
    analysis_window: Optional[AnalysisWindow] = None
    client_risk_profile: str = "balanced"
    extra_context: Dict[str, str] = field(default_factory=dict)

    def validate_required_fields(self) -> List[str]:
        missing_fields = []
        if not self.request_id:
            missing_fields.append("request_id")
        if not self.funds:
            missing_fields.append("funds")
        for index, fund in enumerate(self.funds):
            if not fund.fund_info.code:
                missing_fields.append(f"funds[{index}].fund_info.code")
            if not fund.nav_series:
                missing_fields.append(f"funds[{index}].nav_series")
        return missing_fields

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "funds": [fund.to_dict() for fund in self.funds],
            "analysis_window": self.analysis_window.to_dict() if self.analysis_window else None,
            "client_risk_profile": self.client_risk_profile,
            "extra_context": dict(self.extra_context),
        }


@dataclass
class PortfolioConstituentMetrics:
    """Per-fund metrics computed on the shared aligned date window."""

    code: str
    name: str
    fund_type: str
    normalized_fund_type: str
    weight: float
    nav_points: int
    total_return: float
    annualized_return: float
    annualized_volatility: float
    max_drawdown: float
    sharpe_ratio: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PortfolioAnalysisResult:
    """Portfolio-level analysis output.

    Field names mirror `FinalAnalysisResult` where the meaning is the same
    (`overall_rating`, `overall_score`, `summary`, `quant_metrics`, ...), so the
    frontend can reuse its existing rendering logic. Portfolio-specific data
    lives in `constituents` and the diversification entries of `quant_metrics`.
    """

    request_id: str
    overall_rating: str
    overall_score: float
    summary: str
    score_explanation: str
    key_thesis: List[str]
    main_risks: List[str]
    action_plan: List[str]
    quant_metrics: Dict[str, float]
    constituents: List[PortfolioConstituentMetrics]
    missing_fields: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
    analysis_trace: List[AnalysisTraceEvent] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "overall_rating": self.overall_rating,
            "overall_score": self.overall_score,
            "summary": self.summary,
            "score_explanation": self.score_explanation,
            "key_thesis": list(self.key_thesis),
            "main_risks": list(self.main_risks),
            "action_plan": list(self.action_plan),
            "quant_metrics": dict(self.quant_metrics),
            "constituents": [item.to_dict() for item in self.constituents],
            "missing_fields": list(self.missing_fields),
            "metadata": dict(self.metadata),
            "analysis_trace": [event.to_dict() for event in self.analysis_trace],
        }


@dataclass
class FinalAnalysisResult:
    request_id: str
    overall_rating: str
    overall_score: float
    key_thesis: List[str]
    main_risks: List[str]
    action_plan: List[str]
    agent_outputs: List[AgentOutput]
    summary: str
    score_explanation: str = ""
    missing_fields: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
    analysis_trace: List[AnalysisTraceEvent] = field(default_factory=list)
    quant_metrics: Dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "FinalAnalysisResult":
        payload = payload or {}
        return cls(
            request_id=str(payload.get("request_id", "")),
            overall_rating=str(payload.get("overall_rating", "")),
            overall_score=float(payload.get("overall_score", 0.0)),
            key_thesis=[str(item) for item in payload.get("key_thesis", [])],
            main_risks=[str(item) for item in payload.get("main_risks", [])],
            action_plan=[str(item) for item in payload.get("action_plan", [])],
            agent_outputs=[AgentOutput.from_dict(item) for item in payload.get("agent_outputs", [])],
            summary=str(payload.get("summary", "")),
            score_explanation=str(payload.get("score_explanation", "")),
            missing_fields=[str(item) for item in payload.get("missing_fields", [])],
            metadata={
                str(key): str(value)
                for key, value in (payload.get("metadata") or {}).items()
            },
            analysis_trace=[
                AnalysisTraceEvent.from_dict(item)
                for item in payload.get("analysis_trace", [])
            ],
            quant_metrics={
                str(key): float(value)
                for key, value in (payload.get("quant_metrics") or {}).items()
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
