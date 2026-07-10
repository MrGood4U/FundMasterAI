import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fund_llm import config
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
    AgentOutput,
    BenchmarkInfo,
    FundAnalysisInput,
    FundInfo,
    FundOperationalMetrics,
    NewsItem,
    NavPoint,
)
from fund_llm.feature_builder import FeatureBuilder
from fund_llm.llm_client import MockLLMClient


def build_long_nav_series(point_count: int, start_nav: float = 1.0) -> list[NavPoint]:
    nav = start_nav
    nav_series = []
    for day_index in range(point_count):
        nav_series.append(NavPoint(date=f"2026-02-{day_index + 1:03d}", nav=round(nav, 6)))
        if day_index % 2 == 0:
            nav *= 1.013
        else:
            nav *= 0.995
    return nav_series


def build_sample_input() -> FundAnalysisInput:
    return FundAnalysisInput(
        request_id="demo-003",
        fund_info=FundInfo(
            code="110011",
            name="示例成长混合",
            asset_type="fund_open",
            category="mixed",
            manager="示例经理",
        ),
        nav_series=build_long_nav_series(30),
        industry_exposure={
            "科技": 0.32,
            "医药": 0.18,
            "消费": 0.16,
        },
        top_holdings_weight=0.48,
        news_summary=["成长风格近期相对活跃"],
        news_items=[
            NewsItem(
                title="成长板块成交回暖",
                summary="科技成长方向风险偏好有所修复。",
                published_at="2026-01-05",
                source="示例资讯源",
                topic="成长风格",
                sentiment_label="positive",
            ),
            NewsItem(
                title="波动仍需观察",
                summary="部分高估值资产短期分歧仍在。",
                published_at="2026-01-05",
                source="示例券商",
                topic="估值波动",
                sentiment_label="neutral",
            ),
        ],
        fund_tags=["core_holding", "active_equity", "consumer_tilt"],
        operational_metrics=FundOperationalMetrics(
            fund_size_billion=28.6,
            inception_date="2018-09-05",
            manager_tenure_years=4.5,
        ),
        extra_context={"client_risk_profile": "balanced"},
    )


def build_sample_features():
    return FeatureBuilder().build(build_sample_input())


def build_rich_features():
    payload = build_sample_input()
    payload.nav_series = build_long_nav_series(280)
    payload.benchmark = BenchmarkInfo(code="000300", name="沪深300", asset_type="index")
    payload.benchmark_nav_series = build_long_nav_series(280, start_nav=0.96)
    return FeatureBuilder().build(payload)


def build_bond_input_with_exposure() -> FundAnalysisInput:
    return FundAnalysisInput(
        request_id="bond-003358",
        fund_info=FundInfo(
            code="003358",
            name="易方达中债7-10年期国开行债券指数A",
            asset_type="fund_open",
            category="债券型-债券指数",
            manager="示例经理",
        ),
        nav_series=[
            NavPoint(date="2026-01-01", nav=1.00),
            NavPoint(date="2026-01-02", nav=1.01),
            NavPoint(date="2026-01-03", nav=1.011),
        ],
        bond_holdings=[
            {"bond_code": "200210", "bond_name": "20国开10", "pct": "21.28%", "quarter": "2025Q4"},
            {"bond_code": "210203", "bond_name": "21国开03", "pct": "19.96%", "quarter": "2025Q4"},
            {"bond_code": "220205", "bond_name": "22国开05", "pct": "15.04%", "quarter": "2025Q4"},
            {"bond_code": "230210", "bond_name": "23国开10", "pct": "13.81%", "quarter": "2025Q4"},
            {"bond_code": "240205", "bond_name": "24国开05", "pct": "13.55%", "quarter": "2025Q4"},
        ],
        asset_allocation={"债券": 0.86, "现金": 0.07, "其他": 0.07},
        extra_context={"client_risk_profile": "income_oriented"},
    )


def build_bond_features_with_exposure():
    return FeatureBuilder().build(build_bond_input_with_exposure())


class BrokenLLMClient:
    def chat(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        raise RuntimeError("mock llm failure")


class NoCallLLMClient:
    def __init__(self):
        self.calls = 0

    def chat(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        self.calls += 1
        raise AssertionError("LLM must not be called for an ineligible analysis")


class AgentsTest(unittest.TestCase):
    def test_performance_agent_returns_structured_output(self):
        result = PerformanceAgent(MockLLMClient("performance narrative")).analyze(build_sample_features())

        self.assertEqual(result.agent_name, "PerformanceAgent")
        self.assertEqual(result.status, "success")
        self.assertIsNotNone(result.score)
        self.assertIn(result.stance, {"positive", "neutral", "negative"})
        self.assertTrue(result.key_points)
        self.assertTrue(result.recommendations)
        self.assertEqual(result.narrative, "performance narrative")

    def test_performance_agent_uses_window_and_benchmark_metrics_when_available(self):
        result = PerformanceAgent(MockLLMClient("rich performance narrative")).analyze(build_rich_features())

        self.assertTrue(any("1-year return" in item for item in result.key_points))
        self.assertTrue(any("excess return" in item for item in result.key_points))
        self.assertNotIn(
            "Available return history is still limited for a fuller trend read.",
            result.risks,
        )

    def test_exposure_agent_returns_structured_output(self):
        result = ExposureAgent(MockLLMClient("exposure narrative")).analyze(build_sample_features())

        self.assertEqual(result.agent_name, "ExposureAgent")
        self.assertEqual(result.status, "success")
        self.assertIsNotNone(result.score)
        self.assertIn(result.stance, {"positive", "neutral", "negative"})
        self.assertTrue(result.key_points)
        self.assertTrue(result.recommendations)
        self.assertEqual(result.narrative, "exposure narrative")

    def test_exposure_agent_uses_contextual_fields_when_available(self):
        result = ExposureAgent(MockLLMClient("rich exposure narrative")).analyze(build_rich_features())

        self.assertTrue(any("Fund role/style tags include" in item for item in result.key_points))
        self.assertTrue(any("Manager tenure" in item for item in result.key_points))
        self.assertIn("Exposure profile looks consistent with a core allocation role.", result.recommendations)
        self.assertGreaterEqual(result.confidence, 0.78)

    def test_bond_exposure_agent_returns_structured_output(self):
        result = BondExposureAgent(MockLLMClient("bond exposure narrative")).analyze(
            build_bond_features_with_exposure()
        )

        self.assertEqual(result.agent_name, "BondExposureAgent")
        self.assertEqual(result.status, "success")
        self.assertIsNotNone(result.score)
        self.assertIn(result.stance, {"positive", "neutral", "negative"})
        self.assertTrue(any("Top bond holding weight is 21.28%." in item for item in result.key_points))
        self.assertTrue(any("Asset allocation shows bond 86.00%" in item for item in result.key_points))
        self.assertEqual(result.narrative, "bond exposure narrative")

    def test_bond_exposure_agent_marks_equity_like_funds_not_applicable(self):
        result = BondExposureAgent(MockLLMClient("unused")).analyze(build_sample_features())

        self.assertEqual(result.status, "skipped")
        self.assertIsNone(result.score)
        self.assertEqual(result.stance, "not_applicable")
        self.assertIn("mixed_fund", result.key_points[0])

    def test_bond_exposure_agent_skips_when_bond_data_is_missing(self):
        payload = build_bond_input_with_exposure()
        payload.bond_holdings = []
        payload.asset_allocation = {}
        result = BondExposureAgent(MockLLMClient("unused")).analyze(FeatureBuilder().build(payload))

        self.assertEqual(result.status, "skipped")
        self.assertIsNone(result.score)
        self.assertEqual(result.stance, "insufficient_data")
        self.assertIn("No bond holdings or asset-allocation data was provided.", result.key_points)

    def test_risk_agent_returns_structured_output(self):
        result = RiskAgent(MockLLMClient("risk narrative")).analyze(build_sample_features())

        self.assertEqual(result.agent_name, "RiskAgent")
        self.assertEqual(result.status, "success")
        self.assertIsNotNone(result.score)
        self.assertIn(result.stance, {"positive", "neutral", "negative"})
        self.assertTrue(result.key_points)
        self.assertTrue(result.recommendations)
        self.assertEqual(result.narrative, "risk narrative")

    def test_risk_agent_uses_windowed_risk_metrics_when_available(self):
        result = RiskAgent(MockLLMClient("rich risk narrative")).analyze(build_rich_features())

        self.assertTrue(any("3-month annualized volatility" in item for item in result.key_points))
        self.assertTrue(any("1-year max drawdown" in item for item in result.key_points))
        self.assertNotIn(
            "Risk history is still too short for a fuller rolling-risk assessment.",
            result.risks,
        )

    def test_nav_agents_abstain_below_rating_floor_without_calling_llm(self):
        for nav_point_count in (1, 2, config.MIN_NAV_POINTS_FOR_RATING - 1):
            with self.subTest(nav_point_count=nav_point_count):
                payload = build_sample_input()
                payload.nav_series = build_long_nav_series(nav_point_count)
                features = FeatureBuilder().build(payload)

                for agent_class in (PerformanceAgent, RiskAgent):
                    with self.subTest(agent=agent_class.__name__):
                        llm = NoCallLLMClient()
                        result = agent_class(llm).analyze(features)

                        self.assertEqual(result.status, "skipped")
                        self.assertIsNone(result.score)
                        self.assertEqual(result.stance, "insufficient_data")
                        self.assertEqual(result.confidence, 0.0)
                        self.assertEqual(llm.calls, 0)
                        self.assertIn(str(config.MIN_NAV_POINTS_FOR_RATING), result.key_points[0])

    def test_sentiment_agent_returns_structured_output(self):
        result = SentimentAgent(MockLLMClient("sentiment narrative")).analyze(build_sample_features())

        self.assertEqual(result.agent_name, "SentimentAgent")
        self.assertEqual(result.status, "success")
        self.assertIsNotNone(result.score)
        self.assertIn(result.stance, {"positive", "neutral", "negative"})
        self.assertTrue(result.key_points)
        self.assertTrue(result.recommendations)
        self.assertEqual(result.narrative, "sentiment narrative")

    def test_sentiment_agent_uses_structured_news_signals_when_available(self):
        result = SentimentAgent(MockLLMClient("rich sentiment narrative")).analyze(build_rich_features())

        self.assertTrue(any("Processed" in item for item in result.key_points))
        self.assertTrue(any("Positive news signals count" in item for item in result.key_points))
        self.assertGreaterEqual(result.confidence, 0.7)

    def test_sentiment_agent_gracefully_degrades_without_news(self):
        payload = build_sample_input()
        payload.news_summary = []
        payload.news_items = []
        result = SentimentAgent(MockLLMClient("no news narrative")).analyze(FeatureBuilder().build(payload))

        self.assertEqual(result.status, "skipped")
        self.assertIsNone(result.score)
        self.assertEqual(result.stance, "insufficient_data")
        self.assertIn("No recent news signal was provided.", result.key_points)
        self.assertIn("Sentiment analysis was skipped because no news or event signals were provided.", result.risks)
        self.assertLessEqual(result.confidence, 0.5)

    def test_sector_agent_returns_structured_output(self):
        result = SectorAgent(MockLLMClient("sector narrative")).analyze(build_sample_features())

        self.assertEqual(result.agent_name, "SectorAgent")
        self.assertEqual(result.status, "success")
        self.assertIsNotNone(result.score)
        self.assertIn(result.stance, {"positive", "neutral", "negative"})
        self.assertTrue(result.key_points)
        self.assertTrue(result.recommendations)
        self.assertEqual(result.narrative, "sector narrative")

    def test_sector_agent_uses_industry_breakdown_when_available(self):
        result = SectorAgent(MockLLMClient("rich sector narrative")).analyze(build_rich_features())

        self.assertTrue(any("Top sector is" in item for item in result.key_points))
        self.assertTrue(any("Sector breadth covers" in item for item in result.key_points))
        self.assertGreaterEqual(result.confidence, 0.7)

    def test_sector_agent_gracefully_degrades_without_industry_breakdown(self):
        payload = build_sample_input()
        payload.industry_exposure = {}
        result = SectorAgent(MockLLMClient("no sector narrative")).analyze(FeatureBuilder().build(payload))

        self.assertEqual(result.status, "skipped")
        self.assertIsNone(result.score)
        self.assertEqual(result.stance, "insufficient_data")
        self.assertIn("No industry exposure breakdown was provided.", result.key_points)
        self.assertIn("Sector analysis was skipped because industry exposure data is missing.", result.risks)

    def test_exposure_agent_skips_when_portfolio_breakdown_is_missing(self):
        payload = build_sample_input()
        payload.industry_exposure = {}
        payload.top_holdings_weight = None
        result = ExposureAgent(MockLLMClient("unused")).analyze(FeatureBuilder().build(payload))

        self.assertEqual(result.status, "skipped")
        self.assertIsNone(result.score)
        self.assertEqual(result.stance, "insufficient_data")
        self.assertIn("Portfolio exposure data was not provided.", result.key_points)

    def test_exposure_agent_marks_bond_funds_not_applicable(self):
        payload = build_sample_input()
        payload.fund_info.category = "债券型-债券指数"
        payload.industry_exposure = {}
        payload.top_holdings_weight = None

        result = ExposureAgent(MockLLMClient("unused")).analyze(FeatureBuilder().build(payload))

        self.assertEqual(result.status, "skipped")
        self.assertEqual(result.stance, "not_applicable")
        self.assertIn("bond_index_fund", result.key_points[0])

    def test_sentiment_agent_skips_when_news_is_missing(self):
        payload = build_sample_input()
        payload.news_summary = []
        payload.news_items = []
        result = SentimentAgent(MockLLMClient("unused")).analyze(FeatureBuilder().build(payload))

        self.assertEqual(result.status, "skipped")
        self.assertIsNone(result.score)
        self.assertEqual(result.stance, "insufficient_data")
        self.assertIn("No recent news signal was provided.", result.key_points)

    def test_sector_agent_marks_bond_funds_not_applicable(self):
        payload = build_sample_input()
        payload.fund_info.category = "债券型-债券指数"
        payload.industry_exposure = {}

        result = SectorAgent(MockLLMClient("unused")).analyze(FeatureBuilder().build(payload))

        self.assertEqual(result.status, "skipped")
        self.assertEqual(result.stance, "not_applicable")
        self.assertIn("bond_index_fund", result.key_points[0])

    def test_llm_failure_preserves_all_deterministic_specialist_results(self):
        equity_features = build_sample_features()
        market_payload = build_sample_input()
        market_payload.individual_analysis = [
            {"period": "近1年", "risk_return_ratio_vs_peers": 72, "risk_robustness_vs_peers": 58}
        ]
        market_payload.profit_probability = [
            {"holding_period": "满1年", "profit_probability": 62, "average_return": 12.4}
        ]
        market_features = FeatureBuilder().build(market_payload)
        cases = [
            (PerformanceAgent, equity_features),
            (ExposureAgent, equity_features),
            (RiskAgent, equity_features),
            (SentimentAgent, equity_features),
            (SectorAgent, equity_features),
            (MarketAgent, market_features),
            (BondExposureAgent, build_bond_features_with_exposure()),
        ]

        for agent_class, features in cases:
            with self.subTest(agent=agent_class.__name__):
                result = agent_class(BrokenLLMClient()).safe_analyze(features)

                self.assertEqual(result.agent_name, agent_class.__name__)
                self.assertEqual(result.status, "success")
                self.assertIsNotNone(result.score)
                self.assertGreater(result.confidence, 0.0)
                self.assertEqual(result.metadata["narrative_source"], "deterministic_fallback")
                self.assertIn("optional LLM explanation was unavailable", result.narrative)
                self.assertNotIn("mock llm failure", result.narrative)

    def test_safe_analyze_sanitizes_true_deterministic_failures(self):
        class BrokenDeterministicAgent(PerformanceAgent):
            def analyze(self, features):
                raise RuntimeError("secret deterministic failure detail")

        result = BrokenDeterministicAgent(MockLLMClient("unused")).safe_analyze(
            build_sample_features()
        )

        self.assertEqual(result.agent_name, "PerformanceAgent")
        self.assertEqual(result.status, "error")
        self.assertIsNone(result.score)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.metadata["failure_stage"], "deterministic_analysis")
        self.assertNotIn("secret deterministic failure detail", result.narrative)
        self.assertNotIn("secret deterministic failure detail", " ".join(result.risks))


class MarketAgentTest(unittest.TestCase):
    def build_peer_input(self):
        payload = build_sample_input()
        payload.individual_analysis = [
            {
                "period": "近1年",
                "risk_return_ratio_vs_peers": 77,
                "risk_robustness_vs_peers": 40,
                "annualized_sharpe_ratio": 2.59,
            },
            {
                "period": "近3年",
                "risk_return_ratio_vs_peers": 76,
                "risk_robustness_vs_peers": 52,
            },
        ]
        payload.profit_probability = [
            {"holding_period": "满6个月", "profit_probability": 55, "average_return": 6.19},
            {"holding_period": "满3年", "profit_probability": 71, "average_return": 43.57},
        ]
        return payload

    def test_market_agent_succeeds_with_peer_evidence(self):
        features = FeatureBuilder().build(self.build_peer_input())
        result = MarketAgent(MockLLMClient("market narrative")).analyze(features)

        self.assertEqual(result.agent_name, "MarketAgent")
        self.assertEqual(result.status, "success")
        self.assertIsNotNone(result.score)
        self.assertIn(result.stance, {"positive", "neutral", "negative"})
        self.assertTrue(any("outperforms 77% of peers" in point for point in result.key_points))
        self.assertTrue(any("71% when held for 满3年" in point for point in result.key_points))
        self.assertEqual(result.narrative, "market narrative")

    def test_market_agent_flags_weak_robustness_and_short_horizon(self):
        payload = self.build_peer_input()
        payload.individual_analysis = [
            {"period": "近1年", "risk_return_ratio_vs_peers": 30, "risk_robustness_vs_peers": 35},
        ]
        payload.profit_probability = [
            {"holding_period": "满6个月", "profit_probability": 42, "average_return": 1.0},
        ]
        features = FeatureBuilder().build(payload)

        result = MarketAgent(MockLLMClient("weak narrative")).analyze(features)

        self.assertEqual(result.status, "success")
        self.assertLess(result.score, 55)
        self.assertTrue(any("lags most peers" in risk for risk in result.risks))
        self.assertTrue(any("below-50% profit probability" in risk for risk in result.risks))

    def test_market_agent_skips_without_upstream_data(self):
        features = FeatureBuilder().build(build_sample_input())
        result = MarketAgent(MockLLMClient("unused")).analyze(features)

        self.assertEqual(result.status, "skipped")
        self.assertIsNone(result.score)
        self.assertEqual(result.stance, "insufficient_data")
        self.assertEqual(result.confidence, 0.0)
        self.assertIn(
            "No peer-comparison or holding-period probability data was provided.",
            result.key_points,
        )

    def test_market_agent_ignores_rows_without_parsable_numbers(self):
        payload = build_sample_input()
        payload.individual_analysis = [{"period": "近1年", "risk_return_ratio_vs_peers": "N/A"}]
        payload.profit_probability = [{"holding_period": "满1年", "profit_probability": None}]
        features = FeatureBuilder().build(payload)

        result = MarketAgent(MockLLMClient("unused")).analyze(features)

        self.assertEqual(result.status, "skipped")
        self.assertEqual(result.stance, "insufficient_data")


class DataDrivenConfidenceTest(unittest.TestCase):
    """Phase C：Performance/Risk 置信度必须随数据质量变化，且约束在 0.4-0.9。"""

    def test_performance_confidence_is_high_with_rich_data(self):
        result = PerformanceAgent(MockLLMClient("narrative")).analyze(build_rich_features())

        self.assertGreaterEqual(result.confidence, 0.8)
        self.assertLessEqual(result.confidence, 0.9)

    def test_performance_confidence_is_low_with_sparse_data(self):
        result = PerformanceAgent(MockLLMClient("narrative")).analyze(build_sample_features())

        self.assertGreaterEqual(result.confidence, 0.4)
        self.assertLessEqual(result.confidence, 0.55)

    def test_risk_confidence_is_high_with_rich_data(self):
        result = RiskAgent(MockLLMClient("narrative")).analyze(build_rich_features())

        self.assertGreaterEqual(result.confidence, 0.8)
        self.assertLessEqual(result.confidence, 0.9)

    def test_risk_confidence_is_low_with_sparse_data(self):
        result = RiskAgent(MockLLMClient("narrative")).analyze(build_sample_features())

        self.assertGreaterEqual(result.confidence, 0.4)
        self.assertLessEqual(result.confidence, 0.55)

    def test_confidence_helper_respects_required_flags(self):
        from fund_llm.agents.base import data_driven_confidence

        features = build_rich_features()
        full = data_driven_confidence(features, required_flags=["has_benchmark"])
        missing = data_driven_confidence(features, required_flags=["has_bond_holdings"])

        self.assertGreater(full, missing)
        self.assertGreaterEqual(missing, 0.4)
        self.assertLessEqual(full, 0.9)


class ChiefAgentTest(unittest.TestCase):
    @staticmethod
    def _successful_output(agent_name: str, score: float) -> AgentOutput:
        stance = "positive" if score >= 70 else "negative" if score <= 40 else "neutral"
        return AgentOutput(
            agent_name=agent_name,
            status="success",
            score=score,
            stance=stance,
            key_points=[f"{agent_name} completed."],
            risks=[],
            recommendations=[f"Use the {agent_name} evidence."],
            confidence=0.75,
            narrative=f"{agent_name} narrative",
        )

    @staticmethod
    def _error_output(agent_name: str) -> AgentOutput:
        return AgentOutput(
            agent_name=agent_name,
            status="error",
            score=None,
            stance="mixed",
            key_points=[],
            risks=[f"{agent_name} could not complete its deterministic analysis."],
            recommendations=["Review the server logs and retry the analysis."],
            confidence=0.0,
            narrative=f"{agent_name} could not complete its deterministic analysis.",
        )

    @staticmethod
    def _not_applicable_output(agent_name: str) -> AgentOutput:
        return AgentOutput(
            agent_name=agent_name,
            status="skipped",
            score=None,
            stance="not_applicable",
            key_points=[f"{agent_name} is not applicable."],
            risks=[],
            recommendations=[],
            confidence=0.0,
            narrative=f"{agent_name} is not applicable.",
        )

    def test_chief_abstains_when_nav_history_is_below_rating_floor(self):
        payload = build_sample_input()
        payload.nav_series = build_long_nav_series(2)
        features = FeatureBuilder().build(payload)
        llm = NoCallLLMClient()
        chief = ChiefAgent(llm)
        agent_outputs = [
            AgentOutput(
                agent_name="PerformanceAgent",
                status="success",
                score=100.0,
                stance="positive",
                key_points=["Short sample appears strong."],
                risks=[],
                recommendations=[],
                confidence=0.9,
                narrative="performance narrative",
            ),
            AgentOutput(
                agent_name="RiskAgent",
                status="success",
                score=100.0,
                stance="positive",
                key_points=["Short sample appears calm."],
                risks=[],
                recommendations=[],
                confidence=0.9,
                narrative="risk narrative",
            ),
        ]

        result = chief.aggregate(features, agent_outputs)

        self.assertEqual(result.overall_rating, "insufficient_data")
        self.assertIsNone(result.overall_score)
        self.assertEqual(result.metadata["analysis_status"], "insufficient_data")
        self.assertEqual(result.metadata["rating_eligible"], "false")
        self.assertEqual(result.quant_metrics, {"sample_size": 2.0})
        self.assertEqual(result.metadata["summary_source"], "deterministic_abstention")
        self.assertEqual(llm.calls, 0)
        self.assertNotIn(result.overall_rating, {"buy", "hold", "watch", "avoid"})

    def test_chief_agent_aggregates_outputs(self):
        features = build_sample_features()
        chief = ChiefAgent(MockLLMClient("chief summary"))
        agent_outputs = [
            AgentOutput(
                agent_name="PerformanceAgent",
                status="success",
                score=80.0,
                stance="positive",
                key_points=["收益表现较强。"],
                risks=["短期波动仍需观察。"],
                recommendations=["适合继续跟踪。"],
                confidence=0.8,
                narrative="performance narrative",
            ),
            AgentOutput(
                agent_name="ExposureAgent",
                status="success",
                score=60.0,
                stance="neutral",
                key_points=["行业集中度中等。"],
                risks=["集中度需要持续监控。"],
                recommendations=["与其他风格配置搭配。"],
                confidence=0.7,
                narrative="exposure narrative",
            ),
            AgentOutput(
                agent_name="RiskAgent",
                status="success",
                score=40.0,
                stance="negative",
                key_points=["波动率偏高。"],
                risks=["回撤容忍度要求较高。"],
                recommendations=["控制仓位。"],
                confidence=0.75,
                narrative="risk narrative",
            ),
            AgentOutput(
                agent_name="SentimentAgent",
                status="success",
                score=60.0,
                stance="neutral",
                key_points=["News signal is balanced."],
                risks=[],
                recommendations=["Keep news as a secondary signal."],
                confidence=0.7,
                narrative="sentiment narrative",
            ),
        ]

        result = chief.aggregate(features, agent_outputs)

        self.assertEqual(result.request_id, features.request_id)
        self.assertEqual(result.overall_score, 60.0)
        self.assertEqual(result.overall_rating, "hold")
        self.assertEqual(result.summary, "chief summary")
        self.assertIn("HOLD rating", result.score_explanation)
        self.assertIn("Performance scored 80.0", result.score_explanation)
        self.assertIn("Risk control scored 40.0", result.score_explanation)
        self.assertEqual(len(result.agent_outputs), 4)
        self.assertTrue(result.key_thesis)
        self.assertTrue(result.main_risks)
        self.assertTrue(result.action_plan)

    def test_chief_agent_enriches_output_with_contextual_metadata(self):
        features = build_rich_features()
        chief = ChiefAgent(MockLLMClient("chief summary"))
        agent_outputs = [
            AgentOutput(
                agent_name="PerformanceAgent",
                status="success",
                score=80.0,
                stance="positive",
                key_points=["收益表现较强。"],
                risks=["短期波动仍需观察。"],
                recommendations=["适合继续跟踪。"],
                confidence=0.8,
                narrative="performance narrative",
            ),
            AgentOutput(
                agent_name="ExposureAgent",
                status="success",
                score=60.0,
                stance="neutral",
                key_points=["行业集中度中等。"],
                risks=["集中度需要持续监控。"],
                recommendations=["与其他风格配置搭配。"],
                confidence=0.7,
                narrative="exposure narrative",
            ),
            AgentOutput(
                agent_name="RiskAgent",
                status="success",
                score=40.0,
                stance="negative",
                key_points=["波动率偏高。"],
                risks=["回撤容忍度要求较高。"],
                recommendations=["控制仓位。"],
                confidence=0.75,
                narrative="risk narrative",
            ),
            AgentOutput(
                agent_name="SentimentAgent",
                status="success",
                score=66.0,
                stance="neutral",
                key_points=["Processed 2 recent news signal(s)."],
                risks=[],
                recommendations=["Use recent news flow only as a secondary cross-check alongside fundamentals."],
                confidence=0.8,
                narrative="sentiment narrative",
            ),
            AgentOutput(
                agent_name="SectorAgent",
                status="success",
                score=64.0,
                stance="neutral",
                key_points=["Top sector is 科技 at 32.00%."],
                risks=[],
                recommendations=["Sector positioning looks reasonably balanced for diversified allocation."],
                confidence=0.76,
                narrative="sector narrative",
            ),
        ]

        result = chief.aggregate(features, agent_outputs)

        self.assertEqual(result.metadata["success_agent_count"], "5")
        self.assertEqual(result.metadata["error_agent_count"], "0")
        self.assertEqual(result.metadata["has_benchmark"], "true")
        self.assertEqual(result.metadata["has_news_signal"], "true")
        self.assertEqual(result.metadata["has_sector_context"], "true")
        self.assertEqual(result.metadata["news_item_count"], "2")
        self.assertEqual(result.metadata["client_risk_profile"], "balanced")
        self.assertTrue(any("Benchmark-relative context is available" in item for item in result.key_thesis))
        self.assertTrue(any("Recent news flow is available" in item for item in result.key_thesis))
        self.assertTrue(any("Sector exposure breakdown is available" in item for item in result.key_thesis))
        self.assertTrue(any("balanced risk profile" in item for item in result.action_plan))

    def test_chief_publishes_partial_rating_for_one_non_core_error_without_penalty(self):
        features = build_sample_features()
        chief = ChiefAgent(MockLLMClient("partial chief summary"))
        agent_outputs = [
            AgentOutput(
                agent_name="PerformanceAgent",
                status="success",
                score=75.0,
                stance="positive",
                key_points=["收益保持韧性。"],
                risks=[],
                recommendations=["继续跟踪。"],
                confidence=0.78,
                narrative="performance narrative",
            ),
            AgentOutput(
                agent_name="RiskAgent",
                status="success",
                score=65.0,
                stance="neutral",
                key_points=["Risk remains manageable."],
                risks=[],
                recommendations=["Monitor volatility."],
                confidence=0.74,
                narrative="risk narrative",
            ),
            AgentOutput(
                agent_name="ExposureAgent",
                status="success",
                score=70.0,
                stance="positive",
                key_points=["Exposure remains acceptable."],
                risks=[],
                recommendations=["Monitor concentration."],
                confidence=0.72,
                narrative="exposure narrative",
            ),
            AgentOutput(
                agent_name="SectorAgent",
                status="success",
                score=70.0,
                stance="positive",
                key_points=["Sector evidence remains constructive."],
                risks=[],
                recommendations=["Monitor sector concentration."],
                confidence=0.71,
                narrative="sector narrative",
            ),
            AgentOutput(
                agent_name="SentimentAgent",
                status="error",
                score=None,
                stance="mixed",
                key_points=[],
                risks=["SentimentAgent could not complete its deterministic analysis."],
                recommendations=["Review the server logs and retry the analysis."],
                confidence=0.0,
                narrative="SentimentAgent could not complete its deterministic analysis.",
            ),
        ]

        result = chief.aggregate(features, agent_outputs)

        self.assertEqual(result.metadata["error_agent_count"], "1")
        self.assertEqual(result.metadata["agent_health"], "partial")
        self.assertEqual(result.metadata["analysis_status"], "partial")
        self.assertEqual(result.overall_rating, "hold")
        self.assertEqual(result.overall_score, 70.0)
        self.assertEqual(result.metadata["rating_eligible"], "true")
        self.assertEqual(result.metadata["rating_scored_agent_count"], "4")
        self.assertEqual(result.metadata["rating_applicable_agent_count"], "6")
        self.assertAlmostEqual(float(result.metadata["rating_coverage_ratio"]), 0.67)
        self.assertTrue(any("failed technically" in item for item in result.main_risks))
        self.assertNotIn("penalty", result.score_explanation.lower())

    def test_five_of_six_successes_publish_partial_rating_without_error_penalty(self):
        features = build_sample_features()
        chief = ChiefAgent(MockLLMClient("partial chief summary"))
        agent_outputs = [
            self._successful_output("PerformanceAgent", 80.0),
            self._successful_output("RiskAgent", 60.0),
            self._successful_output("ExposureAgent", 70.0),
            self._successful_output("SentimentAgent", 50.0),
            self._successful_output("SectorAgent", 40.0),
            self._error_output("MarketAgent"),
        ]

        result = chief.aggregate(features, agent_outputs)

        self.assertEqual(result.metadata["analysis_status"], "partial")
        self.assertEqual(result.metadata["rating_scored_agent_count"], "5")
        self.assertEqual(result.metadata["rating_applicable_agent_count"], "6")
        self.assertEqual(float(result.metadata["rating_coverage_ratio"]), round(5 / 6, 2))
        self.assertEqual(result.overall_score, 60.0)
        self.assertEqual(result.overall_rating, "hold")
        self.assertEqual(result.metadata["rating_eligible"], "true")

    def test_exact_sixty_percent_scoring_coverage_is_rating_eligible(self):
        payload = build_bond_input_with_exposure()
        payload.nav_series = build_long_nav_series(config.MIN_NAV_POINTS_FOR_RATING)
        features = FeatureBuilder().build(payload)
        chief = ChiefAgent(MockLLMClient("partial chief summary"))
        agent_outputs = [
            self._successful_output("PerformanceAgent", 75.0),
            self._successful_output("RiskAgent", 65.0),
            self._successful_output("BondExposureAgent", 70.0),
            self._error_output("SentimentAgent"),
            self._error_output("MarketAgent"),
            self._not_applicable_output("ExposureAgent"),
            self._not_applicable_output("SectorAgent"),
        ]

        result = chief.aggregate(features, agent_outputs)

        self.assertEqual(result.metadata["analysis_status"], "partial")
        self.assertEqual(result.metadata["rating_scored_agent_count"], "3")
        self.assertEqual(result.metadata["rating_applicable_agent_count"], "5")
        self.assertAlmostEqual(float(result.metadata["rating_coverage_ratio"]), 0.60)
        self.assertEqual(result.overall_score, 70.0)
        self.assertEqual(result.overall_rating, "hold")
        self.assertEqual(result.metadata["rating_eligible"], "true")

    def test_fewer_than_three_scores_cannot_publish_rating(self):
        features = build_sample_features()
        chief = ChiefAgent(MockLLMClient("unused"))
        agent_outputs = [
            self._successful_output("PerformanceAgent", 80.0),
            self._successful_output("RiskAgent", 60.0),
            self._error_output("ExposureAgent"),
        ]

        result = chief.aggregate(features, agent_outputs)

        self.assertEqual(result.metadata["rating_scored_agent_count"], "2")
        self.assertEqual(result.metadata["rating_applicable_agent_count"], "6")
        self.assertAlmostEqual(float(result.metadata["rating_coverage_ratio"]), 0.33)
        self.assertEqual(result.overall_rating, "unavailable")
        self.assertIsNone(result.overall_score)
        self.assertEqual(result.metadata["rating_eligible"], "false")

    def test_below_sixty_percent_scoring_coverage_cannot_publish_rating(self):
        features = build_sample_features()
        chief = ChiefAgent(MockLLMClient("unused"))
        agent_outputs = [
            self._successful_output("PerformanceAgent", 80.0),
            self._successful_output("RiskAgent", 60.0),
            self._successful_output("ExposureAgent", 70.0),
        ]

        result = chief.aggregate(features, agent_outputs)

        self.assertEqual(result.metadata["rating_scored_agent_count"], "3")
        self.assertEqual(result.metadata["rating_applicable_agent_count"], "6")
        self.assertAlmostEqual(float(result.metadata["rating_coverage_ratio"]), 0.50)
        self.assertEqual(result.overall_rating, "unavailable")
        self.assertIsNone(result.overall_score)
        self.assertEqual(result.metadata["rating_eligible"], "false")

    def test_core_agent_failure_blocks_rating_even_with_high_overall_coverage(self):
        features = build_sample_features()
        chief = ChiefAgent(MockLLMClient("unused"))
        agent_outputs = [
            self._successful_output("PerformanceAgent", 80.0),
            self._error_output("RiskAgent"),
            self._successful_output("ExposureAgent", 70.0),
            self._successful_output("SentimentAgent", 60.0),
            self._successful_output("SectorAgent", 55.0),
            self._successful_output("MarketAgent", 50.0),
            self._not_applicable_output("BondExposureAgent"),
        ]

        result = chief.aggregate(features, agent_outputs)

        self.assertEqual(result.metadata["rating_scored_agent_count"], "5")
        self.assertEqual(result.metadata["rating_applicable_agent_count"], "6")
        self.assertGreater(float(result.metadata["rating_coverage_ratio"]), 0.60)
        self.assertEqual(result.overall_rating, "unavailable")
        self.assertIsNone(result.overall_score)
        self.assertEqual(result.metadata["rating_eligible"], "false")

    def test_rating_coverage_deduplicates_names_and_rejects_invalid_scores(self):
        features = build_sample_features()
        chief = ChiefAgent(MockLLMClient("partial chief summary"))
        agent_outputs = [
            self._successful_output("PerformanceAgent", 80.0),
            self._successful_output("PerformanceAgent", 20.0),
            self._successful_output("RiskAgent", 60.0),
            self._successful_output("ExposureAgent", 70.0),
            self._successful_output("SectorAgent", 50.0),
            self._successful_output("SentimentAgent", float("nan")),
            self._successful_output("MarketAgent", 101.0),
            self._not_applicable_output("BondExposureAgent"),
        ]

        result = chief.aggregate(features, agent_outputs)

        self.assertEqual(result.metadata["rating_scored_agent_count"], "3")
        self.assertEqual(result.metadata["rating_applicable_agent_count"], "6")
        self.assertAlmostEqual(float(result.metadata["rating_coverage_ratio"]), 0.50)
        self.assertEqual(result.metadata["analysis_status"], "technical_error")
        self.assertEqual(result.metadata["rating_eligible"], "false")
        self.assertEqual(result.overall_rating, "unavailable")
        self.assertIsNone(result.overall_score)

    def test_one_high_score_and_six_errors_cannot_publish_buy(self):
        features = build_sample_features()
        chief = ChiefAgent(MockLLMClient("unused"))
        agent_outputs = [
            AgentOutput(
                agent_name="PerformanceAgent",
                status="success",
                score=100.0,
                stance="positive",
                key_points=["Performance score is high."],
                risks=[],
                recommendations=[],
                confidence=0.9,
                narrative="performance narrative",
            )
        ]
        for agent_name in (
            "ExposureAgent",
            "BondExposureAgent",
            "RiskAgent",
            "SentimentAgent",
            "SectorAgent",
            "MarketAgent",
        ):
            agent_outputs.append(
                AgentOutput(
                    agent_name=agent_name,
                    status="error",
                    score=None,
                    stance="mixed",
                    key_points=[],
                    risks=[f"{agent_name} could not complete its deterministic analysis."],
                    recommendations=["Review the server logs and retry the analysis."],
                    confidence=0.0,
                    narrative=f"{agent_name} could not complete its deterministic analysis.",
                )
            )

        result = chief.aggregate(features, agent_outputs)

        self.assertEqual(result.metadata["error_agent_count"], "6")
        self.assertEqual(result.metadata["analysis_status"], "technical_error")
        self.assertEqual(result.overall_rating, "unavailable")
        self.assertIsNone(result.overall_score)
        self.assertNotEqual(result.overall_rating, "buy")

    def test_chief_fallback_summary_does_not_turn_zero_missing_fields_into_limitation(self):
        features = build_sample_features()
        chief = ChiefAgent(BrokenLLMClient())
        agent_outputs = [
            AgentOutput(
                agent_name="PerformanceAgent",
                status="success",
                score=80.0,
                stance="positive",
                key_points=["Performance is strong."],
                risks=[],
                recommendations=["Monitor performance."],
                confidence=0.8,
                narrative="performance narrative",
            ),
            AgentOutput(
                agent_name="RiskAgent",
                status="success",
                score=40.0,
                stance="negative",
                key_points=["Risk is elevated."],
                risks=["Drawdown remains meaningful."],
                recommendations=["Control position size."],
                confidence=0.75,
                narrative="risk narrative",
            ),
            AgentOutput(
                agent_name="ExposureAgent",
                status="success",
                score=60.0,
                stance="neutral",
                key_points=["Exposure is balanced."],
                risks=[],
                recommendations=["Monitor concentration."],
                confidence=0.7,
                narrative="exposure narrative",
            ),
            AgentOutput(
                agent_name="SentimentAgent",
                status="success",
                score=60.0,
                stance="neutral",
                key_points=["News signal is balanced."],
                risks=[],
                recommendations=["Keep news as a secondary signal."],
                confidence=0.7,
                narrative="sentiment narrative",
            ),
        ]

        result = chief.aggregate(features, agent_outputs)

        self.assertIn("not a direct prompt-only answer", result.summary)
        self.assertIn("No required payload fields are missing", result.summary)
        self.assertNotIn("0 missing field", result.summary)

    def test_chief_agent_does_not_treat_not_applicable_as_unhealthy(self):
        payload = build_sample_input()
        payload.fund_info.category = "债券型-债券指数"
        payload.industry_exposure = {}
        payload.top_holdings_weight = None
        features = FeatureBuilder().build(payload)
        chief = ChiefAgent(MockLLMClient("bond chief summary"))
        agent_outputs = [
            AgentOutput(
                agent_name="PerformanceAgent",
                status="success",
                score=70.0,
                stance="positive",
                key_points=["NAV history is available."],
                risks=[],
                recommendations=["Continue monitoring."],
                confidence=0.8,
                narrative="performance narrative",
            ),
            self._successful_output("RiskAgent", 65.0),
            self._successful_output("BondExposureAgent", 60.0),
            self._successful_output("SentimentAgent", 55.0),
            self._successful_output("MarketAgent", 50.0),
            ExposureAgent(MockLLMClient("unused")).analyze(features),
            SectorAgent(MockLLMClient("unused")).analyze(features),
        ]

        result = chief.aggregate(features, agent_outputs)

        self.assertEqual(result.metadata["not_applicable_agent_count"], "2")
        self.assertEqual(result.metadata["skipped_agent_count"], "0")
        self.assertEqual(result.metadata["agent_health"], "healthy")
        self.assertTrue(any("not applicable" in item for item in result.key_thesis))


if __name__ == "__main__":
    unittest.main()
