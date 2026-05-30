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
