from fund_llm.agents import (
    BondExposureAgent,
    ChiefAgent,
    ExposureAgent,
    MarketAgent,
    PerformanceAgent,
    RiskAgent,
    SectorAgent,
    SentimentAgent,
)
from fund_llm.contracts import (
    AnalysisWindow,
    BenchmarkInfo,
    FinalAnalysisResult,
    FundAnalysisInput,
    FundInfo,
    FundOperationalMetrics,
    NewsItem,
    NavPoint,
)
from fund_llm.feature_builder import FeatureBuilder
from fund_llm.llm_client import MockLLMClient
from fund_llm.orchestration.engine import AnalysisEngine


def _build_demo_nav_series(
    start_nav: float,
    up_factor: float,
    down_factor: float,
    point_count: int = 30,
) -> list[NavPoint]:
    nav = start_nav
    points = []
    for index in range(point_count):
        points.append(NavPoint(date=f"2026-01-{index + 1:02d}", nav=round(nav, 6)))
        nav *= up_factor if index % 3 else down_factor
    return points


def build_mock_input() -> FundAnalysisInput:
    """Build a stable demo payload for local development and smoke tests."""

    return FundAnalysisInput(
        request_id="mock-demo-001",
        fund_info=FundInfo(
            code="005827",
            name="易方达蓝筹精选混合",
            asset_type="fund_open",
            category="mixed",
            manager="张坤",
        ),
        nav_series=_build_demo_nav_series(1.0, up_factor=1.008, down_factor=0.996),
        industry_exposure={
            "食品饮料": 0.35,
            "互联网": 0.20,
            "医药": 0.15,
        },
        top_holdings_weight=0.58,
        individual_analysis=[
            {
                "period": "近1年",
                "annualized_sharpe_ratio": 1.42,
                "annualized_volatility": 21.5,
                "max_drawdown": 14.2,
                "risk_return_ratio_vs_peers": 72,
                "risk_robustness_vs_peers": 58,
            },
            {
                "period": "近3年",
                "annualized_sharpe_ratio": 0.61,
                "annualized_volatility": 23.8,
                "max_drawdown": 28.4,
                "risk_return_ratio_vs_peers": 64,
                "risk_robustness_vs_peers": 51,
            },
        ],
        profit_probability=[
            {"holding_period": "满6个月", "profit_probability": 56, "average_return": 5.8},
            {"holding_period": "满1年", "profit_probability": 62, "average_return": 12.4},
            {"holding_period": "满3年", "profit_probability": 70, "average_return": 38.9},
        ],
        news_summary=[
            "消费板块热度回升",
            "白酒行业预期改善",
        ],
        news_items=[
            NewsItem(
                title="消费板块热度回升，机构关注龙头估值修复",
                summary="近期消费板块成交活跃，市场预期龙头公司盈利稳定性回升。",
                published_at="2026-01-04",
                source="Mock Finance Wire",
                topic="消费复苏",
                sentiment_label="positive",
            ),
            NewsItem(
                title="白酒行业预期改善，但短期波动仍在",
                summary="机构认为行业需求边际改善，不过市场情绪仍有反复。",
                published_at="2026-01-05",
                source="Mock Sellside Research",
                topic="白酒行业",
                sentiment_label="neutral",
            ),
        ],
        analysis_window=AnalysisWindow(
            start_date="2025-01-01",
            end_date="2026-01-30",
            as_of_date="2026-01-30",
        ),
        benchmark=BenchmarkInfo(
            code="000300",
            name="沪深300",
        ),
        benchmark_nav_series=_build_demo_nav_series(1.0, up_factor=1.005, down_factor=0.997),
        fund_tags=["core_holding", "active_equity", "consumer_tilt"],
        operational_metrics=FundOperationalMetrics(
            fund_size_billion=28.6,
            inception_date="2018-09-05",
            manager_tenure_years=4.5,
        ),
        extra_context={
            "client_risk_profile": "balanced",
            "distribution_channel": "mobile_app",
        },
    )


def build_mock_engine(
    mock_response: str = "Mock analysis narrative.",
    max_parallel_agents: int = None,
) -> AnalysisEngine:
    llm_client = MockLLMClient(mock_response)
    return AnalysisEngine(
        feature_builder=FeatureBuilder(),
        agents=[
            PerformanceAgent(llm_client),
            ExposureAgent(llm_client),
            BondExposureAgent(llm_client),
            RiskAgent(llm_client),
            SentimentAgent(llm_client),
            SectorAgent(llm_client),
            MarketAgent(llm_client),
        ],
        chief_agent=ChiefAgent(llm_client),
        max_workers=max_parallel_agents,
    )


def run_mock_analysis(
    mock_response: str = "Mock analysis narrative.",
    max_parallel_agents: int = None,
) -> FinalAnalysisResult:
    engine = build_mock_engine(mock_response=mock_response, max_parallel_agents=max_parallel_agents)
    payload = build_mock_input()
    return engine.run(payload)


def run_mock_analysis_as_dict(mock_response: str = "Mock analysis narrative.") -> dict:
    return run_mock_analysis(mock_response=mock_response).to_dict()


def run_mock_analysis_for_input(
    payload: FundAnalysisInput,
    mock_response: str = "Mock analysis narrative.",
    max_parallel_agents: int = None,
) -> FinalAnalysisResult:
    engine = build_mock_engine(mock_response=mock_response, max_parallel_agents=max_parallel_agents)
    return engine.run(payload)
