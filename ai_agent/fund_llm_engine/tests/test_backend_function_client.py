import unittest

from fund_llm.adapters.backend_function_client import (
    BackendFunctionClient,
    BackendService,
    build_fund_input_from_backend_functions,
)


def test_backend_function_client_discovers_and_calls_post_tool():
    calls = []

    def transport(method, url, payload, timeout):
        calls.append((method, url, payload, timeout))
        if url.endswith("/api/market/functions?tag=fund"):
            return {
                "code": 200,
                "data": [
                    {
                        "name": "get_fund_hist",
                        "path": "/api/market/fund_public/hist",
                        "method": "POST",
                        "parameters": {"type": "object", "properties": {}},
                    }
                ],
                "message": "success",
            }
        if url.endswith("/api/market/fund_public/hist"):
            return {"code": 200, "data": [{"date": "2026-01-01", "unit_net_value": 1.0}]}
        return {"code": 200, "data": []}

    client = BackendFunctionClient(
        services={
            "market": BackendService("market", "http://market", "/api/market/functions"),
            "news": BackendService("news", "http://news", "/api/news/functions"),
            "portfolio": BackendService("portfolio", "http://portfolio", "/api/portfolio/functions"),
        },
        transport=transport,
    )
    client.discover("market", tag="fund")
    data = client.call("get_fund_hist", {"code": "000001"})

    assert data == [{"date": "2026-01-01", "unit_net_value": 1.0}]
    assert calls[-1][0] == "POST"
    assert calls[-1][2] == {"code": "000001"}


def test_build_fund_input_from_backend_functions_maps_core_fields():
    def transport(method, url, payload, timeout):
        if "/functions" in url:
            if "market" in url:
                return {
                    "code": 200,
                    "data": [
                        {"name": "get_fund_hist", "path": "/hist", "method": "POST", "parameters": {}},
                        {"name": "get_fund_individual_basic_info", "path": "/basic", "method": "POST", "parameters": {}},
                        {"name": "get_fund_portfolio_holds", "path": "/holds", "method": "POST", "parameters": {}},
                        {"name": "get_fund_individual_analysis", "path": "/analysis", "method": "POST", "parameters": {}},
                        {"name": "get_fund_profit_probability", "path": "/profit", "method": "POST", "parameters": {}},
                    ],
                    "message": "success",
                }
            return {
                "code": 200,
                "data": [
                    {"name": "get_public_fund_announcement", "path": "/ann", "method": "POST", "parameters": {}}
                ],
                "message": "success",
            }
        if url.endswith("/hist"):
            return {
                "code": 200,
                "data": [
                    {"date": "2026-01-01", "unit_net_value": "1.00"},
                    {"date": "2026-01-02", "unit_net_value": "1.04"},
                ],
            }
        if url.endswith("/basic"):
            return {
                "code": 200,
                "data": [
                    {
                        "fund_name": "Demo Fund",
                        "fund_type": "mixed",
                        "fund_manager": "Manager A",
                        "latest_aum": "25.0亿元",
                        "inception_date": "2020-01-01",
                    }
                ],
            }
        if url.endswith("/holds"):
            return {
                "code": 200,
                "data": [
                    {"stock_name": "A", "net_value_pct": "15.5", "quarter": "2025Q4"},
                    {"stock_name": "B", "net_value_pct": "9.5", "quarter": "2025Q4"},
                ],
            }
        if url.endswith("/ann"):
            return {
                "code": 200,
                "data": [
                    {
                        "announcement_title": "Dividend announcement",
                        "announcement_date": "2026-01-03",
                    }
                ],
            }
        return {"code": 200, "data": []}

    services = {
        "market": BackendService("market", "http://market", "/api/market/functions"),
        "news": BackendService("news", "http://news", "/api/news/functions"),
        "portfolio": BackendService("portfolio", "http://portfolio", "/api/portfolio/functions"),
    }
    client = BackendFunctionClient(services=services, transport=transport)

    payload = build_fund_input_from_backend_functions("000001", client=client, portfolio_year="2025")

    assert payload.fund_info.name == "Demo Fund"
    assert payload.fund_info.manager == "Manager A"
    assert len(payload.nav_series) == 2
    assert payload.top_holdings_weight == 0.25
    assert len(payload.news_items) == 1
    assert payload.operational_metrics.fund_size_billion == 2.5
    assert payload.extra_context["data_source"] == "backend_function_registry"
    assert payload.extra_context["normalized_fund_type"] == "mixed_fund"
    assert "get_fund_hist" in payload.extra_context["available_backend_tools"]


def test_build_fund_input_treats_small_holding_percentages_as_percent_units():
    def transport(method, url, payload, timeout):
        if "/functions" in url:
            if "market" in url:
                return {
                    "code": 200,
                    "data": [
                        {"name": "get_fund_hist", "path": "/hist", "method": "POST", "parameters": {}},
                        {"name": "get_fund_individual_basic_info", "path": "/basic", "method": "POST", "parameters": {}},
                        {"name": "get_fund_portfolio_holds", "path": "/holds", "method": "POST", "parameters": {}},
                        {"name": "get_fund_individual_analysis", "path": "/analysis", "method": "POST", "parameters": {}},
                        {"name": "get_fund_profit_probability", "path": "/profit", "method": "POST", "parameters": {}},
                    ],
                    "message": "success",
                }
            return {
                "code": 200,
                "data": [
                    {"name": "get_public_fund_announcement", "path": "/ann", "method": "POST", "parameters": {}}
                ],
                "message": "success",
            }
        if url.endswith("/hist"):
            return {
                "code": 200,
                "data": [
                    {"date": "2026-01-01", "unit_net_value": "1.00"},
                    {"date": "2026-01-02", "unit_net_value": "1.04"},
                ],
            }
        if url.endswith("/basic"):
            return {"code": 200, "data": [{"fund_name": "Index Fund", "fund_type": "股票型-标准指数"}]}
        if url.endswith("/holds"):
            return {
                "code": 200,
                "data": [
                    {"stock_name": "A", "net_value_pct": 18.33, "quarter": "2026年1季度股票投资明细"},
                    {"stock_name": "B", "net_value_pct": 0.70, "quarter": "2026年1季度股票投资明细"},
                    {"stock_name": "C", "net_value_pct": 16.14, "quarter": "2026年1季度股票投资明细"},
                ],
            }
        return {"code": 200, "data": []}

    services = {
        "market": BackendService("market", "http://market", "/api/market/functions"),
        "news": BackendService("news", "http://news", "/api/news/functions"),
        "portfolio": BackendService("portfolio", "http://portfolio", "/api/portfolio/functions"),
    }
    client = BackendFunctionClient(services=services, transport=transport)

    payload = build_fund_input_from_backend_functions("161725", client=client, top_holdings_n=2)

    assert round(payload.top_holdings_weight, 4) == 0.3447
    assert '"stock_name": "A"' in payload.extra_context["top_holdings"]
    assert '"stock_name": "C"' in payload.extra_context["top_holdings"]
    assert '"stock_name": "B"' not in payload.extra_context["top_holdings"]


def test_build_fund_input_applies_start_date_even_without_end_date():
    def transport(method, url, payload, timeout):
        if "/functions" in url:
            if "market" in url:
                return {
                    "code": 200,
                    "data": [
                        {"name": "get_fund_hist", "path": "/hist", "method": "POST", "parameters": {}},
                        {"name": "get_fund_individual_basic_info", "path": "/basic", "method": "POST", "parameters": {}},
                        {"name": "get_fund_portfolio_holds", "path": "/holds", "method": "POST", "parameters": {}},
                        {"name": "get_fund_individual_analysis", "path": "/analysis", "method": "POST", "parameters": {}},
                        {"name": "get_fund_profit_probability", "path": "/profit", "method": "POST", "parameters": {}},
                    ],
                    "message": "success",
                }
            return {
                "code": 200,
                "data": [
                    {"name": "get_public_fund_announcement", "path": "/ann", "method": "POST", "parameters": {}}
                ],
                "message": "success",
            }
        if url.endswith("/hist"):
            return {
                "code": 200,
                "data": [
                    {"date": "2025-01-01", "unit_net_value": "1.00"},
                    {"date": "2026-01-01", "unit_net_value": "1.10"},
                    {"date": "2026-01-02", "unit_net_value": "1.21"},
                ],
            }
        if url.endswith("/basic"):
            return {"code": 200, "data": [{"fund_name": "Demo Fund", "fund_type": "混合型-偏股"}]}
        return {"code": 200, "data": []}

    services = {
        "market": BackendService("market", "http://market", "/api/market/functions"),
        "news": BackendService("news", "http://news", "/api/news/functions"),
        "portfolio": BackendService("portfolio", "http://portfolio", "/api/portfolio/functions"),
    }
    client = BackendFunctionClient(services=services, transport=transport)

    payload = build_fund_input_from_backend_functions("000001", client=client, start_date="2026-01-01")

    assert [point.date for point in payload.nav_series] == ["2026-01-01", "2026-01-02"]
    assert payload.analysis_window.start_date == "2026-01-01"


class BackendFunctionClientRegressionTest(unittest.TestCase):
    def test_small_holding_percentages_are_run_by_unittest(self):
        test_build_fund_input_treats_small_holding_percentages_as_percent_units()

    def test_start_date_filter_is_run_by_unittest(self):
        test_build_fund_input_applies_start_date_even_without_end_date()


if __name__ == "__main__":
    unittest.main()
