from fund_llm.agents import (
    BondExposureAgent,
    ChiefAgent,
    ExposureAgent,
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
        nav_series=[
            NavPoint(date="2026-01-01", nav=1.00),
            NavPoint(date="2026-01-02", nav=1.05),
            NavPoint(date="2026-01-03", nav=1.02),
            NavPoint(date="2026-01-04", nav=1.10),
            NavPoint(date="2026-01-05", nav=1.08),
        ],
        industry_exposure={
            "食品饮料": 0.35,
            "互联网": 0.20,
            "医药": 0.15,
        },
        top_holdings_weight=0.58,
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
            end_date="2026-01-05",
            as_of_date="2026-01-05",
        ),
        benchmark=BenchmarkInfo(
            code="000300",
            name="沪深300",
        ),
        benchmark_nav_series=[
            NavPoint(date="2026-01-01", nav=1.00),
            NavPoint(date="2026-01-02", nav=1.03),
            NavPoint(date="2026-01-03", nav=1.01),
            NavPoint(date="2026-01-04", nav=1.05),
            NavPoint(date="2026-01-05", nav=1.04),
        ],
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
