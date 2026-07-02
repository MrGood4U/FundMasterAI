import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from fund_llm.contracts import (  # noqa: E402
    AnalysisWindow,
    FundInfo,
    NavPoint,
    PortfolioAnalysisInput,
    PortfolioFundData,
)


def load_agent_app():
    spec = importlib.util.spec_from_file_location("fundmaster_agent_portfolio_app", ROOT / "app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


agent_app = load_agent_app()


def build_nav_series(drift_up: float, drift_down: float, point_count: int = 90):
    nav = 1.0
    series = []
    for day_index in range(point_count):
        series.append(
            NavPoint(
                date=f"2026-{(day_index // 28) + 1:02d}-{(day_index % 28) + 1:02d}",
                nav=round(nav, 6),
            )
        )
        nav *= drift_up if day_index % 2 == 0 else drift_down
    return series


def build_backend_portfolio_payload() -> PortfolioAnalysisInput:
    fund_a = PortfolioFundData(
        fund_info=FundInfo(
            code="000001",
            name="Demo Mixed Fund",
            asset_type="fund_open",
            category="混合型-偏股",
        ),
        nav_series=build_nav_series(1.015, 0.995),
        weight=0.6,
        requested_weight=60,
    )
    fund_b = PortfolioFundData(
        fund_info=FundInfo(
            code="003358",
            name="Demo Bond Index Fund",
            asset_type="fund_open",
            category="债券型-债券指数",
        ),
        nav_series=build_nav_series(0.999, 1.004),
        weight=0.4,
        requested_weight=40,
    )
    return PortfolioAnalysisInput(
        request_id="backend-portfolio-000001-003358-2026-04-06",
        funds=[fund_a, fund_b],
        analysis_window=AnalysisWindow(start_date="2026-01-01", end_date="2026-04-06"),
        client_risk_profile="balanced",
        extra_context={
            "data_source": "backend_function_registry",
            "weights_rescaled": "true",
            "fund_count": "2",
            "available_backend_tools": "get_fund_hist,get_fund_individual_basic_info",
            "successful_backend_tools": "get_fund_hist,get_fund_individual_basic_info",
            "errored_backend_tools": "",
            "tool_trace": "[]",
        },
    )


class PortfolioApiContractTest(unittest.TestCase):
    def setUp(self):
        self.client = agent_app.create_app().test_client()

    def assert_keys(self, payload, expected_keys):
        self.assertTrue(
            set(expected_keys).issubset(payload),
            f"Missing keys: {sorted(set(expected_keys) - set(payload))}",
        )

    def test_portfolio_analyze_success_matches_contract(self):
        with patch.object(
            agent_app,
            "build_portfolio_input_from_backend_functions",
            return_value=build_backend_portfolio_payload(),
        ):
            response = self.client.post(
                "/api/ai/portfolio/analyze",
                json={
                    "positions": [
                        {"code": "000001", "weight": 60},
                        {"code": "003358", "weight": 40},
                    ],
                    "mock": True,
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["code"], 200)
        self.assertEqual(body["message"], "success")
        self.assert_keys(body, ["code", "data", "coverage", "message"])

        data = body["data"]
        self.assert_keys(
            data,
            [
                "request_id",
                "overall_rating",
                "overall_score",
                "summary",
                "score_explanation",
                "key_thesis",
                "main_risks",
                "action_plan",
                "quant_metrics",
                "constituents",
                "missing_fields",
                "metadata",
                "analysis_trace",
            ],
        )
        self.assertIn(data["overall_rating"], {"buy", "hold", "watch", "avoid"})
        self.assertIsInstance(data["overall_score"], (int, float))
        self.assertEqual(data["metadata"]["analysis_level"], "portfolio")
        self.assertEqual(data["metadata"]["llm_mode"], "mock")

        self.assert_keys(
            data["quant_metrics"],
            [
                "total_return",
                "annualized_return",
                "annualized_volatility",
                "max_drawdown",
                "sharpe_ratio",
                "sortino_ratio",
                "calmar_ratio",
                "positive_period_ratio",
                "weighted_average_volatility",
                "diversification_benefit",
                "sample_size",
            ],
        )
        for metric_name, metric_value in data["quant_metrics"].items():
            self.assertIsInstance(metric_value, (int, float), f"{metric_name} should be numeric")

        self.assertEqual(len(data["constituents"]), 2)
        for constituent in data["constituents"]:
            self.assert_keys(
                constituent,
                [
                    "code",
                    "name",
                    "fund_type",
                    "normalized_fund_type",
                    "weight",
                    "nav_points",
                    "total_return",
                    "annualized_return",
                    "annualized_volatility",
                    "max_drawdown",
                    "sharpe_ratio",
                ],
            )

        self.assertGreater(len(data["analysis_trace"]), 0)
        trace_titles = [event["title"] for event in data["analysis_trace"]]
        self.assertIn("Loaded constituent fund histories", trace_titles)
        self.assertIn("Composed weighted portfolio NAV", trace_titles)
        for event in data["analysis_trace"]:
            self.assert_keys(
                event,
                ["category", "title", "detail", "status", "evidence", "technical"],
            )

        coverage = body["coverage"]
        self.assert_keys(
            coverage,
            [
                "fund_count",
                "funds",
                "weights_rescaled",
                "data_source",
                "available_backend_tools",
                "successful_backend_tools",
                "errored_backend_tools",
            ],
        )
        self.assertEqual(coverage["fund_count"], 2)
        self.assertEqual(coverage["funds"][0]["code"], "000001")
        self.assertEqual(coverage["weights_rescaled"], "true")

    def test_missing_positions_returns_400(self):
        response = self.client.post("/api/ai/portfolio/analyze", json={})

        body = response.get_json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(body["code"], 400)
        self.assertIsNone(body["data"])
        self.assertIn("positions", body["message"])

    def test_backend_nav_failure_returns_422(self):
        with patch.object(
            agent_app,
            "build_portfolio_input_from_backend_functions",
            side_effect=ValueError("No NAV data returned by backend for fund code(s): 000002."),
        ):
            response = self.client.post(
                "/api/ai/portfolio/analyze",
                json={
                    "positions": [
                        {"code": "000001", "weight": 0.5},
                        {"code": "000002", "weight": 0.5},
                    ],
                    "mock": True,
                },
            )

        body = response.get_json()
        self.assertEqual(response.status_code, 422)
        self.assertEqual(body["code"], 422)
        self.assertIsNone(body["data"])
        self.assertIn("000002", body["message"])

    def test_invalid_weight_returns_422_before_backend_calls(self):
        response = self.client.post(
            "/api/ai/portfolio/analyze",
            json={
                "positions": [
                    {"code": "000001", "weight": 0},
                ],
                "mock": True,
            },
        )

        body = response.get_json()
        self.assertEqual(response.status_code, 422)
        self.assertIn("must be positive", body["message"])

    def test_real_mode_accepts_llm_model_override(self):
        captured = {}

        def fake_run_real_portfolio_analysis_for_input(payload, model=None, timeout_seconds=None):
            captured["model"] = model
            captured["timeout_seconds"] = timeout_seconds
            from fund_llm.portfolio_pipeline import run_mock_portfolio_analysis_for_input

            result = run_mock_portfolio_analysis_for_input(payload)
            result.metadata["llm_mode"] = "real"
            result.metadata["llm_model"] = model or ""
            return result

        with patch.object(
            agent_app,
            "build_portfolio_input_from_backend_functions",
            return_value=build_backend_portfolio_payload(),
        ), patch.object(
            agent_app,
            "run_real_portfolio_analysis_for_input",
            side_effect=fake_run_real_portfolio_analysis_for_input,
        ):
            response = self.client.post(
                "/api/ai/portfolio/analyze",
                json={
                    "positions": [
                        {"code": "000001", "weight": 0.6},
                        {"code": "003358", "weight": 0.4},
                    ],
                    "mock": False,
                    "llm_model": "deepseek-v4-pro",
                    "llm_timeout_seconds": 45,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(captured["model"], "deepseek-v4-pro")
        self.assertEqual(captured["timeout_seconds"], 45)
        body = response.get_json()
        self.assertEqual(body["data"]["metadata"]["llm_model"], "deepseek-v4-pro")

    def test_fund_endpoint_contract_is_unchanged(self):
        # 老的单基金端点必须继续工作（向后兼容检查）。
        response = self.client.post("/api/ai/fund/analyze", json={})

        body = response.get_json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(body, {"code": 400, "data": None, "message": "code is required"})


if __name__ == "__main__":
    unittest.main()
