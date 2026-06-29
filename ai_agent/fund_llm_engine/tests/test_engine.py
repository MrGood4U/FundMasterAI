import os
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fund_llm.agents import (
    BondExposureAgent,
    ChiefAgent,
    ExposureAgent,
    PerformanceAgent,
    RiskAgent,
    SectorAgent,
    SentimentAgent,
)
from fund_llm.contracts import AgentOutput, FinalAnalysisResult, FundAnalysisInput, FundInfo, NavPoint, NewsItem
from fund_llm.feature_builder import FeatureBuilder
from fund_llm.llm_client import MockLLMClient
from fund_llm.orchestration.engine import AnalysisEngine


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
        nav_series=[
            NavPoint(date="2026-01-01", nav=1.00),
            NavPoint(date="2026-01-02", nav=1.04),
            NavPoint(date="2026-01-03", nav=1.01),
            NavPoint(date="2026-01-04", nav=1.06),
            NavPoint(date="2026-01-05", nav=1.07),
        ],
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
