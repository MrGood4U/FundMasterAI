import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from fund_llm.contracts import FundInfo  # noqa: E402
from fund_llm.sector_view import SectorViewFund  # noqa: E402


def load_agent_app():
    spec = importlib.util.spec_from_file_location("fundmaster_agent_sector_app", ROOT / "app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


agent_app = load_agent_app()


def build_backend_sector_funds():
    funds = [
        SectorViewFund(
            fund_info=FundInfo(
                code="161725",
                name="招商中证白酒指数",
                asset_type="fund_open",
                category="股票型-标准指数",
            ),
            industry_exposure={"白酒": 0.9434},
        ),
        SectorViewFund(
            fund_info=FundInfo(
                code="003358",
                name="易方达中债7-10年期国开行债券指数A",
                asset_type="fund_open",
                category="债券型-债券指数",
            ),
            industry_exposure={},
        ),
    ]
    context = {
        "data_source": "backend_function_registry",
        "available_backend_tools": "get_fund_individual_basic_info,get_fund_portfolio_industry_allocation",
        "successful_backend_tools": "get_fund_individual_basic_info,get_fund_portfolio_industry_allocation",
        "errored_backend_tools": "",
        "tool_trace": [],
    }
    return funds, context


class SectorApiContractTest(unittest.TestCase):
    def setUp(self):
        self.client = agent_app.create_app().test_client()

    def assert_keys(self, payload, expected_keys):
        self.assertTrue(
            set(expected_keys).issubset(payload),
            f"Missing keys: {sorted(set(expected_keys) - set(payload))}",
        )

    def test_sector_analyze_success_matches_contract(self):
        with patch.object(
            agent_app,
            "build_sector_view_funds_from_backend_functions",
            return_value=build_backend_sector_funds(),
        ):
            response = self.client.post(
                "/api/ai/sector/analyze",
                json={"codes": ["161725", "003358"], "mock": True},
            )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["code"], 200)
        self.assert_keys(body, ["code", "data", "coverage", "message"])

        data = body["data"]
        self.assert_keys(
            data,
            [
                "request_id",
                "status",
                "funds",
                "sector_matrix",
                "sector_total_count",
                "common_sectors",
                "funds_with_data",
                "funds_without_data",
                "summary",
                "metadata",
                "analysis_trace",
            ],
        )
        self.assertEqual(data["status"], "partial")
        self.assertEqual(data["metadata"]["analysis_level"], "sector")
        self.assertEqual(data["metadata"]["llm_mode"], "mock")
        self.assertEqual(len(data["funds"]), 2)
        equity_row = data["funds"][0]
        self.assert_keys(
            equity_row,
            [
                "code",
                "name",
                "fund_type",
                "normalized_fund_type",
                "sector_status",
                "sector_count",
                "top_sector",
                "top_sector_weight",
                "top_sectors",
            ],
        )
        self.assertEqual(equity_row["sector_status"], "available")
        bond_row = data["funds"][1]
        self.assertEqual(bond_row["sector_status"], "not_applicable")

        matrix_row = data["sector_matrix"][0]
        self.assert_keys(
            matrix_row,
            ["sector", "exposures", "funds_holding", "average_weight", "max_weight", "max_fund"],
        )

        coverage = body["coverage"]
        self.assert_keys(
            coverage,
            [
                "fund_count",
                "funds_with_data",
                "funds_without_data",
                "data_source",
                "available_backend_tools",
                "successful_backend_tools",
                "errored_backend_tools",
            ],
        )
        self.assertEqual(coverage["fund_count"], 2)

    def test_codes_accept_position_style_objects(self):
        with patch.object(
            agent_app,
            "build_sector_view_funds_from_backend_functions",
            return_value=build_backend_sector_funds(),
        ) as mocked:
            response = self.client.post(
                "/api/ai/sector/analyze",
                json={"funds": [{"code": "161725"}, {"code": "003358"}], "mock": True},
            )

        self.assertEqual(response.status_code, 200)
        mocked.assert_called_once_with(["161725", "003358"])

    def test_missing_codes_returns_400(self):
        response = self.client.post("/api/ai/sector/analyze", json={})

        body = response.get_json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(body["code"], 400)
        self.assertIn("codes", body["message"])

    def test_duplicate_codes_return_422(self):
        response = self.client.post(
            "/api/ai/sector/analyze",
            json={"codes": ["161725", "161725"], "mock": True},
        )

        body = response.get_json()
        self.assertEqual(response.status_code, 422)
        self.assertIn("more than once", body["message"])


if __name__ == "__main__":
    unittest.main()
