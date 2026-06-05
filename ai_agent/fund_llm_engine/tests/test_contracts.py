import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fund_llm.contracts import AnalysisTraceEvent, FinalAnalysisResult, FundAnalysisInput
from fund_llm.mock_pipeline import build_mock_input, run_mock_analysis


class ContractsTest(unittest.TestCase):
    def test_fund_analysis_input_from_dict_supports_extended_fields(self):
        payload = FundAnalysisInput.from_dict(
            {
                "request_id": "req-001",
                "fund_info": {
                    "code": "000001",
                    "name": "示例基金",
                    "asset_type": "fund_open",
                    "category": "mixed",
                    "manager": "示例经理",
                },
                "nav_series": [
                    {"date": "2026-01-01", "nav": 1.0},
                    {"date": "2026-01-02", "nav": 1.02},
                ],
                "industry_exposure": {"科技": 0.3},
                "top_holdings_weight": 0.45,
                "news_summary": ["示例新闻"],
                "news_items": [
                    {
                        "title": "示例新闻标题",
                        "summary": "示例新闻摘要",
                        "published_at": "2026-01-02",
                        "source": "示例媒体",
                        "topic": "行业景气",
                        "sentiment_label": "positive",
                    }
                ],
                "analysis_window": {
                    "start_date": "2025-01-01",
                    "end_date": "2026-01-02",
                    "as_of_date": "2026-01-02",
                },
                "benchmark": {
                    "code": "000300",
                    "name": "沪深300",
                },
                "benchmark_nav_series": [
                    {"date": "2026-01-01", "nav": 1.0},
                    {"date": "2026-01-02", "nav": 1.01},
                ],
                "fund_tags": ["balanced", "core"],
                "operational_metrics": {
                    "fund_size_billion": 12.5,
                    "inception_date": "2020-01-01",
                    "manager_tenure_years": 2.5,
                },
                "extra_context": {
                    "client_risk_profile": "balanced",
                },
            }
        )

        self.assertEqual(payload.request_id, "req-001")
        self.assertEqual(payload.fund_info.code, "000001")
        self.assertEqual(payload.analysis_window.as_of_date, "2026-01-02")
        self.assertEqual(payload.benchmark.name, "沪深300")
        self.assertEqual(len(payload.benchmark_nav_series), 2)
        self.assertEqual(len(payload.news_items), 1)
        self.assertEqual(payload.news_items[0].topic, "行业景气")
        self.assertEqual(payload.fund_tags, ["balanced", "core"])
        self.assertEqual(payload.operational_metrics.fund_size_billion, 12.5)
        self.assertEqual(payload.extra_context["client_risk_profile"], "balanced")
        self.assertEqual(payload.validate_required_fields(), [])

    def test_fund_analysis_input_validate_required_fields(self):
        payload = FundAnalysisInput.from_dict(
            {
                "request_id": "",
                "fund_info": {
                    "code": "",
                    "name": "",
                    "asset_type": "",
                },
                "nav_series": [],
            }
        )

        self.assertEqual(
            payload.validate_required_fields(),
            [
                "request_id",
                "fund_info.code",
                "fund_info.name",
                "fund_info.asset_type",
                "nav_series",
            ],
        )

    def test_final_analysis_result_round_trip(self):
        result = run_mock_analysis()
        result.analysis_trace.append(
            AnalysisTraceEvent(
                category="backend",
                title="Loaded real fund history",
                detail="Fetched NAV history through the backend function registry.",
                evidence={"nav_points": 5},
                technical={"function": "get_fund_hist"},
            )
        )
        round_tripped = FinalAnalysisResult.from_dict(result.to_dict())

        self.assertEqual(round_tripped.request_id, result.request_id)
        self.assertEqual(round_tripped.summary, result.summary)
        self.assertEqual(round_tripped.missing_fields, result.missing_fields)
        self.assertEqual(len(round_tripped.agent_outputs), len(result.agent_outputs))
        self.assertEqual(round_tripped.analysis_trace[-1].title, "Loaded real fund history")
        self.assertEqual(round_tripped.analysis_trace[-1].evidence["nav_points"], 5)

    def test_mock_input_to_dict_contains_extended_contract_fields(self):
        payload = build_mock_input().to_dict()

        self.assertIn("analysis_window", payload)
        self.assertIn("benchmark", payload)
        self.assertIn("benchmark_nav_series", payload)
        self.assertIn("fund_tags", payload)
        self.assertIn("operational_metrics", payload)
        self.assertIn("extra_context", payload)
        self.assertIn("news_items", payload)


if __name__ == "__main__":
    unittest.main()
