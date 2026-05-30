from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


def _coerce_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    return float(value)


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
    return_metrics: Dict[str, float]
    risk_metrics: Dict[str, float]
    exposure_metrics: Dict[str, float]
    industry_exposure_breakdown: Dict[str, float] = field(default_factory=dict)
    benchmark_metrics: Dict[str, float] = field(default_factory=dict)
    data_quality_metrics: Dict[str, int] = field(default_factory=dict)
    data_quality_flags: Dict[str, bool] = field(default_factory=dict)
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
class FinalAnalysisResult:
    request_id: str
    overall_rating: str
    overall_score: float
    key_thesis: List[str]
    main_risks: List[str]
    action_plan: List[str]
    agent_outputs: List[AgentOutput]
    summary: str
    missing_fields: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)

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
            missing_fields=[str(item) for item in payload.get("missing_fields", [])],
            metadata={
                str(key): str(value)
                for key, value in (payload.get("metadata") or {}).items()
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
