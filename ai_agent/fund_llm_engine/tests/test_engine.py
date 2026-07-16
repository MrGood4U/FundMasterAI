import os
import sys
import threading
import time
import unittest
from statistics import mean

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

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
from fund_llm.contracts import AgentOutput, FinalAnalysisResult, FundAnalysisInput, FundInfo, NavPoint, NewsItem
from fund_llm.feature_builder import FeatureBuilder
from fund_llm.llm_client import MockLLMClient
from fund_llm.orchestration.engine import AnalysisEngine


def build_nav_series(point_count: int = 30) -> list[NavPoint]:
    nav = 1.0
    points = []
    for index in range(point_count):
        points.append(NavPoint(date=f"2026-01-{index + 1:02d}", nav=round(nav, 6)))
        nav *= 1.008 if index % 3 else 0.996
    return points


def build_sample_input() -> FundAnalysisInput:
    return FundAnalysisInput(
        request_id="demo-002",
        fund_info=FundInfo(
            code="159915",
            name="创业板ETF",
            asset_type="etf",
            category="index",
            manager="某基金公司",
        ),
        nav_series=build_nav_series(),
        industry_exposure={"科技": 0.40, "医药": 0.18},
        top_holdings_weight=0.52,
        news_summary=["科技成长板块活跃"],
        news_items=[
            NewsItem(
                title="科技成长板块活跃",
                summary="市场情绪回暖带动成长方向成交改善。",
                published_at="2026-01-05",
                source="示例媒体",
                topic="科技成长",
                sentiment_label="positive",
            )
        ],
    )


class BrokenLLMClient:
    def chat(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        raise RuntimeError("provider unavailable")


class EngineTest(unittest.TestCase):
    def test_full_engine_run(self):
        llm = MockLLMClient("Mock narrative")
        engine = AnalysisEngine(
            feature_builder=FeatureBuilder(),
            agents=[
                PerformanceAgent(llm),
                ExposureAgent(llm),
                BondExposureAgent(llm),
                RiskAgent(llm),
                SentimentAgent(llm),
                SectorAgent(llm),
            ],
            chief_agent=ChiefAgent(llm),
        )

        result = engine.run(build_sample_input())

        self.assertEqual(result.request_id, "demo-002")
        self.assertEqual(len(result.agent_outputs), 6)
        self.assertIn(result.overall_rating, {"buy", "hold", "watch", "avoid"})
        self.assertTrue(result.summary)
        self.assertGreater(result.overall_score, 0)
        self.assertEqual(
            [
                (output.agent_name, output.status, output.stance)
                for output in result.agent_outputs
                if output.agent_name == "BondExposureAgent"
            ],
            [("BondExposureAgent", "skipped", "not_applicable")],
        )
        self.assertEqual(result.metadata["agent_execution_mode"], "parallel")
        self.assertEqual(result.metadata["agent_worker_count"], "6")
        self.assertGreaterEqual(len(result.analysis_trace), 8)
        self.assertEqual(result.analysis_trace[0].title, "Calculated fund metrics")
        self.assertIn("Evaluated performance", [event.title for event in result.analysis_trace])
        self.assertIn("Checked bond exposure", [event.title for event in result.analysis_trace])
        self.assertIn("Combined specialist views", [event.title for event in result.analysis_trace])
        bond_trace = next(
            event
            for event in result.analysis_trace
            if event.technical.get("agent_name") == "BondExposureAgent"
        )
        self.assertEqual(bond_trace.status, "success")

    def test_two_point_nav_jump_abstains_instead_of_publishing_a_rating(self):
        payload = build_sample_input()
        payload.nav_series = [
            NavPoint(date="2026-01-01", nav=1.0),
            NavPoint(date="2026-01-02", nav=1.2),
        ]
        llm = MockLLMClient("Mock narrative")
        engine = AnalysisEngine(
            feature_builder=FeatureBuilder(),
            agents=[
                PerformanceAgent(llm),
                ExposureAgent(llm),
                BondExposureAgent(llm),
                RiskAgent(llm),
                SentimentAgent(llm),
                SectorAgent(llm),
            ],
            chief_agent=ChiefAgent(llm),
        )

        result = engine.run(payload)

        self.assertEqual(result.overall_rating, "insufficient_data")
        self.assertIsNone(result.overall_score)
        self.assertEqual(result.metadata["analysis_status"], "insufficient_data")
        self.assertEqual(result.metadata["rating_eligible"], "false")
        self.assertNotIn(result.overall_rating, {"buy", "hold", "watch", "avoid"})
        self.assertEqual(result.quant_metrics, {"sample_size": 2.0})
        outputs = {output.agent_name: output for output in result.agent_outputs}
        for agent_name in ("PerformanceAgent", "RiskAgent"):
            self.assertEqual(outputs[agent_name].status, "skipped")
            self.assertIsNone(outputs[agent_name].score)
            self.assertEqual(outputs[agent_name].stance, "insufficient_data")
            trace = next(
                event
                for event in result.analysis_trace
                if event.technical.get("agent_name") == agent_name
            )
            self.assertEqual(trace.status, "warning")
        self.assertEqual(result.analysis_trace[-1].status, "warning")
        self.assertEqual(
            result.analysis_trace[-1].technical["analysis_status"],
            "insufficient_data",
        )

    def test_etf_feeder_rating_excludes_direct_exposure_and_sector_scores(self):
        payload = build_sample_input()
        payload.fund_info = FundInfo(
            code="008163",
            name="南方标普红利低波50ETF联接A",
            asset_type="fund_open",
            category="指数型-股票",
        )
        payload.top_holdings_weight = 0.0027
        payload.top_holdings = [{"stock_code": "residual", "weight_fraction": 0.0027}]
        payload.industry_exposure = {"制造业": 0.0022}
        payload.individual_analysis = [
            {
                "period": "近1年",
                "risk_return_ratio_vs_peers": 55,
                "risk_robustness_vs_peers": 60,
            }
        ]
        llm = MockLLMClient("Mock narrative")
        engine = AnalysisEngine(
            feature_builder=FeatureBuilder(),
            agents=[
                PerformanceAgent(llm),
                ExposureAgent(llm),
                BondExposureAgent(llm),
                RiskAgent(llm),
                SentimentAgent(llm),
                SectorAgent(llm),
                MarketAgent(llm),
            ],
            chief_agent=ChiefAgent(llm),
        )

        result = engine.run(payload)
        outputs = {output.agent_name: output for output in result.agent_outputs}
        scored_outputs = [
            output for output in result.agent_outputs if output.status == "success" and output.score is not None
        ]

        self.assertEqual(result.metadata["normalized_fund_type"], "etf_feeder_fund")
        self.assertEqual(result.metadata["has_sector_context"], "false")
        self.assertEqual(outputs["ExposureAgent"].stance, "not_applicable")
        self.assertEqual(outputs["SectorAgent"].stance, "not_applicable")
        self.assertIsNone(outputs["ExposureAgent"].score)
        self.assertIsNone(outputs["SectorAgent"].score)
        self.assertEqual(result.metadata["rating_applicable_agent_count"], "4")
        self.assertEqual(result.metadata["rating_scored_agent_count"], "4")
        self.assertAlmostEqual(
            result.overall_score,
            round(mean(output.score for output in scored_outputs), 2),
        )
        self.assertIn(result.overall_rating, {"buy", "hold", "watch", "avoid"})
        self.assertFalse(
            any("acceptable for diversified allocation" in item for item in result.action_plan)
        )

    def test_provider_outage_preserves_deterministic_final_rating(self):
        def build_engine(llm):
            return AnalysisEngine(
                feature_builder=FeatureBuilder(),
                agents=[
                    PerformanceAgent(llm),
                    ExposureAgent(llm),
                    BondExposureAgent(llm),
                    RiskAgent(llm),
                    SentimentAgent(llm),
                    SectorAgent(llm),
                    MarketAgent(llm),
                ],
                chief_agent=ChiefAgent(llm),
            )

        healthy_payload = build_sample_input()
        healthy_payload.individual_analysis = [
            {
                "period": "近1年",
                "risk_return_ratio_vs_peers": 68,
                "risk_robustness_vs_peers": 61,
            }
        ]
        outage_payload = build_sample_input()
        outage_payload.individual_analysis = list(healthy_payload.individual_analysis)
        healthy_result = build_engine(MockLLMClient("Mock narrative")).run(healthy_payload)
        outage_result = build_engine(BrokenLLMClient()).run(outage_payload)

        self.assertEqual(outage_result.overall_score, healthy_result.overall_score)
        self.assertEqual(outage_result.overall_rating, healthy_result.overall_rating)
        self.assertEqual(outage_result.metadata["analysis_status"], "complete")
        self.assertNotEqual(outage_result.metadata["analysis_status"], "partial")
        self.assertEqual(outage_result.metadata["agent_health"], "degraded")
        self.assertEqual(outage_result.metadata["summary_source"], "deterministic_fallback")
        self.assertEqual(outage_result.metadata["specialist_narrative_fallback_count"], "6")
        self.assertTrue(
            all(
                output.metadata.get("narrative_source") == "deterministic_fallback"
                for output in outage_result.agent_outputs
                if output.status == "success"
            )
        )

    def test_engine_runs_specialist_agents_in_parallel(self):
        state = {"active": 0, "max_active": 0}
        lock = threading.Lock()

        class SlowAgent:
            def __init__(self, name: str):
                self.name = name

            def safe_analyze(self, features):
                with lock:
                    state["active"] += 1
                    state["max_active"] = max(state["max_active"], state["active"])
                try:
                    time.sleep(0.05)
                    return AgentOutput(
                        agent_name=self.name,
                        status="success",
                        score=60,
                        stance="neutral",
                        key_points=[self.name],
                        risks=[],
                        recommendations=[],
                        confidence=0.8,
                        narrative=f"{self.name} narrative",
                    )
                finally:
                    with lock:
                        state["active"] -= 1

        class PassthroughChief:
            def aggregate(self, features, agent_outputs):
                return FinalAnalysisResult(
                    request_id=features.request_id,
                    overall_rating="hold",
                    overall_score=60,
                    key_thesis=[],
                    main_risks=[],
                    action_plan=[],
                    agent_outputs=agent_outputs,
                    summary="done",
                )

        engine = AnalysisEngine(
            feature_builder=FeatureBuilder(),
            agents=[SlowAgent("AgentA"), SlowAgent("AgentB"), SlowAgent("AgentC")],
            chief_agent=PassthroughChief(),
        )

        result = engine.run(build_sample_input())

        self.assertGreater(state["max_active"], 1)
        self.assertEqual([output.agent_name for output in result.agent_outputs], ["AgentA", "AgentB", "AgentC"])
        self.assertEqual(result.metadata["agent_execution_mode"], "parallel")
        self.assertEqual(result.metadata["agent_worker_count"], "3")
        self.assertEqual(result.analysis_trace[-1].technical["execution_mode"], "parallel")


if __name__ == "__main__":
    unittest.main()
