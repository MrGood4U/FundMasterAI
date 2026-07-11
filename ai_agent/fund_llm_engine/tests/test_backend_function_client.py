import unittest
from unittest.mock import patch

from fund_llm.adapters.backend_function_client import (
    BackendFunctionClient,
    BackendFunctionError,
    BackendService,
    build_fund_input_from_backend_functions,
    build_portfolio_input_from_backend_functions,
    build_sector_view_funds_from_backend_functions,
)
from fund_llm.contracts import PortfolioPosition
from fund_llm.feature_builder import FeatureBuilder
from fund_llm.portfolio_analysis import build_holdings_lookthrough


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
                        {"name": "get_fund_portfolio_industry_allocation", "path": "/industry", "method": "POST", "parameters": {}},
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
        if url.endswith("/industry"):
            return {
                "code": 200,
                "data": [
                    {"industry_category": "Technology", "pct": "35.0", "as_of_date": "2025-12-31"},
                    {"industry_category": "Healthcare", "pct": "15.0", "as_of_date": "2025-12-31"},
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
        if url.endswith("/analysis"):
            return {"code": 200, "data": [{"cumulative_return_rank": "top 25%"}]}
        if url.endswith("/profit"):
            return {
                "code": 200,
                "data": [
                    {"holding_period": "6m", "profit_probability": "65.0%"},
                    {"holding_period": "1y", "profit_probability": "78.5%"},
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
    assert payload.industry_exposure == {"Technology": 0.35, "Healthcare": 0.15}
    assert len(payload.news_items) == 1
    assert payload.operational_metrics.fund_size_billion == 2.5
    assert payload.extra_context["data_source"] == "backend_function_registry"
    assert payload.extra_context["normalized_fund_type"] == "mixed_fund"
    assert "get_fund_hist" in payload.extra_context["available_backend_tools"]
    # 结构化字段（不再只存 extra_context 的 JSON 预览字符串）
    assert [row["stock_name"] for row in payload.top_holdings] == ["A", "B"]
    assert payload.profit_probability[-1]["profit_probability"] == "78.5%"
    assert payload.individual_analysis == [{"cumulative_return_rank": "top 25%"}]


def test_build_fund_input_maps_bond_holdings_and_asset_allocation():
    asset_rows = [
        {"asset_type": "债券", "pct": "112.00%"},
        {"asset_type": "现金", "pct": "7.00%"},
        {"asset_type": "其他", "pct": "7.00%"},
    ]
    asset_state = {"return_none": False}

    def transport(method, url, payload, timeout):
        if "/functions" in url:
            if "market" in url:
                return {
                    "code": 200,
                    "data": [
                        {"name": "get_fund_hist", "path": "/hist", "method": "POST", "parameters": {}},
                        {"name": "get_fund_individual_basic_info", "path": "/basic", "method": "POST", "parameters": {}},
                        {"name": "get_fund_portfolio_hold_bond", "path": "/bonds", "method": "POST", "parameters": {}},
                        {"name": "get_fund_individual_detail_hold", "path": "/asset", "method": "POST", "parameters": {}},
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
                    {"date": "2026-01-02", "unit_net_value": "1.01"},
                ],
            }
        if url.endswith("/basic"):
            return {"code": 200, "data": [{"fund_name": "Bond Fund", "fund_type": "index_fixed_income"}]}
        if url.endswith("/bonds"):
            return {
                "code": 200,
                "data": [
                    {"bond_name": "Old Bond", "pct": "30.00", "quarter": "2025Q3"},
                    {"bond_name": "20国开10", "pct": "21.28", "quarter": "2025Q4"},
                    {"bond_name": "21国开03", "pct": "19.96", "quarter": "2025Q4"},
                    {"bond_name": "Small Bond", "pct": "0.59", "quarter": "2025Q4"},
                ],
            }
        if url.endswith("/asset"):
            return {
                "code": 200,
                "data": None if asset_state["return_none"] else list(asset_rows),
            }
        return {"code": 200, "data": []}

    services = {
        "market": BackendService("market", "http://market", "/api/market/functions"),
        "news": BackendService("news", "http://news", "/api/news/functions"),
        "portfolio": BackendService("portfolio", "http://portfolio", "/api/portfolio/functions"),
    }
    client = BackendFunctionClient(services=services, transport=transport)

    payload = build_fund_input_from_backend_functions("003358", client=client, portfolio_year="2025")

    assert payload.fund_info.category == "index_fixed_income"
    assert [item["bond_name"] for item in payload.bond_holdings] == [
        "20国开10",
        "21国开03",
        "Small Bond",
    ]
    assert [round(item["weight_fraction"], 4) for item in payload.bond_holdings] == [
        0.2128,
        0.1996,
        0.0059,
    ]
    assert payload.asset_allocation == {"债券": 1.12, "现金": 0.07, "其他": 0.07}
    assert payload.invalid_asset_allocation_count == 0
    assert payload.extra_context["normalized_fund_type"] == "bond_index_fund"
    assert payload.extra_context["bond_holdings_count"] == "3"
    assert payload.extra_context["asset_allocation_count"] == "3"

    features = FeatureBuilder().build(payload)
    assert round(features.bond_exposure_metrics["bond_top_holding_weight"], 4) == 0.2128
    assert round(features.bond_exposure_metrics["bond_top_three_weight"], 4) == 0.4183
    assert round(features.bond_exposure_metrics["bond_total_disclosed_weight"], 4) == 0.4183
    assert round(features.bond_exposure_metrics["asset_bond_weight"], 4) == 1.12
    assert features.data_quality_flags["bond_holdings_valid"] is True
    assert features.data_quality_flags["asset_allocation_valid"] is True

    asset_rows.append({"asset_type": "损坏字段", "pct": "not-a-percentage"})
    invalid_payload = build_fund_input_from_backend_functions(
        "003358", client=client, portfolio_year="2025"
    )
    invalid_features = FeatureBuilder().build(invalid_payload)

    assert invalid_payload.asset_allocation == payload.asset_allocation
    assert invalid_payload.invalid_asset_allocation_count == 1
    assert invalid_payload.extra_context["asset_allocation_count"] == "4"
    assert invalid_payload.extra_context["invalid_asset_allocation_count"] == "1"
    assert invalid_features.data_quality_flags["has_asset_allocation"] is True
    assert invalid_features.data_quality_flags["asset_allocation_valid"] is False

    asset_state["return_none"] = True
    empty_payload = build_fund_input_from_backend_functions(
        "003358", client=client, portfolio_year="2025"
    )
    assert empty_payload.asset_allocation == {}
    assert empty_payload.invalid_asset_allocation_count == 0
    assert empty_payload.extra_context["asset_allocation_count"] == "0"


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


def test_build_fund_input_does_not_truncate_explicit_start_date_window():
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
                    {"date": "2025-01-02", "unit_net_value": "1.01"},
                    {"date": "2025-01-03", "unit_net_value": "1.02"},
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

    payload = build_fund_input_from_backend_functions(
        "000001",
        client=client,
        start_date="2025-01-01",
        max_nav_points=2,
    )

    assert [point.date for point in payload.nav_series] == [
        "2025-01-01",
        "2025-01-02",
        "2025-01-03",
    ]


def test_build_fund_input_uses_latest_news_announcements():
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
            return {"code": 200, "data": [{"fund_name": "Demo Fund", "fund_type": "混合型-偏股"}]}
        if url.endswith("/ann"):
            return {
                "code": 200,
                "data": [
                    {"announcement_title": "Old dividend", "announcement_date": "Thu, 11 Jan 2007 00:00:00 GMT"},
                    {"announcement_title": "Newest dividend", "announcement_date": "Thu, 18 Sep 2025 00:00:00 GMT"},
                    {"announcement_title": "Recent dividend", "announcement_date": "2023-01-10"},
                    {"announcement_title": "Undated dividend"},
                ],
            }
        return {"code": 200, "data": []}

    services = {
        "market": BackendService("market", "http://market", "/api/market/functions"),
        "news": BackendService("news", "http://news", "/api/news/functions"),
        "portfolio": BackendService("portfolio", "http://portfolio", "/api/portfolio/functions"),
    }
    client = BackendFunctionClient(services=services, transport=transport)

    payload = build_fund_input_from_backend_functions(
        "000001",
        client=client,
        max_news_items=2,
    )

    assert [item.title for item in payload.news_items] == ["Newest dividend", "Recent dividend"]
    assert [item.published_at for item in payload.news_items] == ["2025-09-18", "2023-01-10"]


def test_optional_bond_timeout_is_not_retried_across_years():
    calls = []

    def transport(method, url, payload, timeout):
        calls.append((method, url, payload, timeout))
        if "/functions" in url:
            if "market" in url:
                return {
                    "code": 200,
                    "data": [
                        {"name": "get_fund_hist", "path": "/hist", "method": "POST", "parameters": {}},
                        {"name": "get_fund_individual_basic_info", "path": "/basic", "method": "POST", "parameters": {}},
                        {"name": "get_fund_portfolio_hold_bond", "path": "/bonds", "method": "POST", "parameters": {}},
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
                    {"date": "2026-01-02", "unit_net_value": "1.01"},
                ],
            }
        if url.endswith("/basic"):
            return {"code": 200, "data": [{"fund_name": "Mixed Fund", "fund_type": "混合型-偏股"}]}
        if url.endswith("/bonds"):
            raise TimeoutError("timed out")
        return {"code": 200, "data": []}

    services = {
        "market": BackendService("market", "http://market", "/api/market/functions"),
        "news": BackendService("news", "http://news", "/api/news/functions"),
        "portfolio": BackendService("portfolio", "http://portfolio", "/api/portfolio/functions"),
    }
    client = BackendFunctionClient(services=services, transport=transport, timeout_seconds=120)

    with patch.dict("os.environ", {"BACKEND_OPTIONAL_FUNCTION_TIMEOUT_SECONDS": "7"}):
        payload = build_fund_input_from_backend_functions("000001", client=client)

    bond_calls = [call for call in calls if call[1].endswith("/bonds")]
    assert len(bond_calls) == 1
    assert bond_calls[0][3] == 7
    assert payload.bond_holdings == []
    assert "get_fund_portfolio_hold_bond" in payload.extra_context["errored_backend_tools"]


def _portfolio_transport_factory(nav_by_code, basic_by_code=None, failing_codes=None):
    basic_by_code = basic_by_code or {}
    failing_codes = failing_codes or set()

    def transport(method, url, payload, timeout):
        if "/functions" in url:
            if "market" in url:
                return {
                    "code": 200,
                    "data": [
                        {"name": "get_fund_hist", "path": "/hist", "method": "POST", "parameters": {}},
                        {"name": "get_fund_individual_basic_info", "path": "/basic", "method": "POST", "parameters": {}},
                    ],
                    "message": "success",
                }
            return {"code": 200, "data": [], "message": "success"}
        code = (payload or {}).get("code", "")
        if url.endswith("/hist"):
            if code in failing_codes:
                return {"code": 500, "data": None, "message": "no data"}
            return {"code": 200, "data": nav_by_code.get(code, [])}
        if url.endswith("/basic"):
            return {"code": 200, "data": [basic_by_code.get(code, {})]}
        return {"code": 200, "data": []}

    return transport


def _portfolio_services():
    return {
        "market": BackendService("market", "http://market", "/api/market/functions"),
        "news": BackendService("news", "http://news", "/api/news/functions"),
        "portfolio": BackendService("portfolio", "http://portfolio", "/api/portfolio/functions"),
    }


def test_build_portfolio_input_fetches_nav_and_basic_info_per_fund():
    # 两只基金的日期范围刻意不一致：000001 多一个更早的点，003358 多一个更晚的点。
    # analysis_window 必须取共同交集（01-01..01-02），而不是并集（2025-12-30..01-03）。
    nav_by_code = {
        "000001": [
            {"date": "2025-12-30", "unit_net_value": "0.99"},
            {"date": "2026-01-01", "unit_net_value": "1.00"},
            {"date": "2026-01-02", "unit_net_value": "1.02"},
        ],
        "003358": [
            {"date": "2026-01-01", "unit_net_value": "2.00"},
            {"date": "2026-01-02", "unit_net_value": "2.01"},
            {"date": "2026-01-03", "unit_net_value": "2.02"},
        ],
    }
    basic_by_code = {
        "000001": {"fund_name": "Mixed Demo", "fund_type": "混合型-偏股"},
        "003358": {"fund_name": "Bond Demo", "fund_type": "债券型-债券指数"},
    }
    client = BackendFunctionClient(
        services=_portfolio_services(),
        transport=_portfolio_transport_factory(nav_by_code, basic_by_code),
    )
    positions = [
        PortfolioPosition(code="000001", weight=60),
        PortfolioPosition(code="003358", weight=40),
    ]

    payload = build_portfolio_input_from_backend_functions(positions, client=client)

    assert len(payload.funds) == 2
    assert payload.funds[0].fund_info.name == "Mixed Demo"
    assert payload.funds[1].fund_info.category == "债券型-债券指数"
    assert round(payload.funds[0].weight, 4) == 0.6
    assert payload.funds[0].requested_weight == 60
    assert payload.extra_context["weights_rescaled"] == "true"
    assert payload.extra_context["fund_count"] == "2"
    assert payload.analysis_window.start_date == "2026-01-01"
    assert payload.analysis_window.end_date == "2026-01-02"
    assert payload.request_id.endswith("2026-01-02")


def test_build_portfolio_input_fetches_lookthrough_data_per_fund():
    # 000001 是权益基金：有股票持仓、行业配置、资产配置；
    # 003358 是债券指数：这三类都没有，应降级为空而不是报错。
    def transport(method, url, payload, timeout):
        code = (payload or {}).get("code", "")
        if "/functions" in url:
            if "market" in url:
                return {
                    "code": 200,
                    "data": [
                        {"name": "get_fund_hist", "path": "/hist", "method": "POST", "parameters": {}},
                        {"name": "get_fund_individual_basic_info", "path": "/basic", "method": "POST", "parameters": {}},
                        {"name": "get_fund_portfolio_holds", "path": "/holds", "method": "POST", "parameters": {}},
                        {"name": "get_fund_portfolio_industry_allocation", "path": "/industry", "method": "POST", "parameters": {}},
                        {"name": "get_fund_individual_detail_hold", "path": "/asset", "method": "POST", "parameters": {}},
                    ],
                    "message": "success",
                }
            return {"code": 200, "data": [], "message": "success"}
        if url.endswith("/hist"):
            return {
                "code": 200,
                "data": [
                    {"date": "2026-01-01", "unit_net_value": "1.00"},
                    {"date": "2026-01-02", "unit_net_value": "1.02"},
                ],
            }
        if url.endswith("/basic"):
            fund_type = "混合型-偏股" if code == "000001" else "债券型-债券指数"
            return {"code": 200, "data": [{"fund_name": f"Fund {code}", "fund_type": fund_type}]}
        if url.endswith("/holds"):
            if code != "000001":
                return {"code": 200, "data": []}
            return {
                "code": 200,
                "data": [
                    {"stock_code": "600519", "stock_name": "贵州茅台", "net_value_pct": "9.5", "quarter": "2026Q1"},
                    {"stock_code": "000858", "stock_name": "五粮液", "net_value_pct": "7.2", "quarter": "2026Q1"},
                    {"stock_code": "000001", "stock_name": "小比例持仓", "net_value_pct": "0.70", "quarter": "2026Q1"},
                ],
            }
        if url.endswith("/industry"):
            if code != "000001":
                return {"code": 200, "data": []}
            return {"code": 200, "data": [{"industry_category": "食品饮料", "pct": "35.0"}]}
        if url.endswith("/asset"):
            if code != "000001":
                return {"code": 200, "data": []}
            return {
                "code": 200,
                "data": [
                    {"asset_type": "股票", "pct": "88.0"},
                    {"asset_type": "现金", "pct": "10.0"},
                ],
            }
        return {"code": 200, "data": []}

    client = BackendFunctionClient(services=_portfolio_services(), transport=transport)
    positions = [
        PortfolioPosition(code="000001", weight=0.6),
        PortfolioPosition(code="003358", weight=0.4),
    ]

    payload = build_portfolio_input_from_backend_functions(positions, client=client)

    equity_fund, bond_fund = payload.funds
    assert [row["stock_name"] for row in equity_fund.top_holdings] == [
        "贵州茅台",
        "五粮液",
        "小比例持仓",
    ]
    assert round(equity_fund.top_holdings[-1]["weight_fraction"], 4) == 0.007
    assert equity_fund.industry_exposure == {"食品饮料": 0.35}
    assert equity_fund.asset_allocation == {"股票": 0.88, "现金": 0.10}
    assert bond_fund.top_holdings == []
    assert bond_fund.industry_exposure == {}
    assert bond_fund.asset_allocation == {}
    assert payload.extra_context["lookthrough_enabled"] == "true"

    lookthrough = build_holdings_lookthrough(payload.funds)
    small_position = next(
        row for row in lookthrough["top_holdings"] if row["stock_name"] == "小比例持仓"
    )
    self_weight = small_position["held_by"][0]["weight_in_fund"]
    assert round(self_weight, 4) == 0.007
    assert round(small_position["portfolio_weight"], 4) == 0.0042


def test_build_portfolio_input_can_skip_lookthrough_fetch():
    calls = []

    def transport(method, url, payload, timeout):
        calls.append(url)
        if "/functions" in url:
            if "market" in url:
                return {
                    "code": 200,
                    "data": [
                        {"name": "get_fund_hist", "path": "/hist", "method": "POST", "parameters": {}},
                        {"name": "get_fund_individual_basic_info", "path": "/basic", "method": "POST", "parameters": {}},
                        {"name": "get_fund_portfolio_holds", "path": "/holds", "method": "POST", "parameters": {}},
                    ],
                    "message": "success",
                }
            return {"code": 200, "data": [], "message": "success"}
        if url.endswith("/hist"):
            return {
                "code": 200,
                "data": [
                    {"date": "2026-01-01", "unit_net_value": "1.00"},
                    {"date": "2026-01-02", "unit_net_value": "1.02"},
                ],
            }
        if url.endswith("/basic"):
            return {"code": 200, "data": [{"fund_name": "Demo", "fund_type": "mixed"}]}
        return {"code": 200, "data": []}

    client = BackendFunctionClient(services=_portfolio_services(), transport=transport)

    payload = build_portfolio_input_from_backend_functions(
        [PortfolioPosition(code="000001", weight=1.0)],
        client=client,
        include_lookthrough=False,
    )

    assert payload.funds[0].top_holdings == []
    assert payload.extra_context["lookthrough_enabled"] == "false"
    assert not any(url.endswith("/holds") for url in calls)


def test_build_portfolio_input_with_disjoint_calendars_leaves_window_empty():
    # 完全无共同日期时不在取数层报错（留给管线的最小重叠检查给出 422），
    # 但 window 必须为空，request_id 使用占位符而不是并集日期。
    nav_by_code = {
        "000001": [{"date": "2026-01-01", "unit_net_value": "1.00"}],
        "003358": [{"date": "2026-02-01", "unit_net_value": "2.00"}],
    }
    client = BackendFunctionClient(
        services=_portfolio_services(),
        transport=_portfolio_transport_factory(nav_by_code),
    )
    positions = [
        PortfolioPosition(code="000001", weight=0.5),
        PortfolioPosition(code="003358", weight=0.5),
    ]

    payload = build_portfolio_input_from_backend_functions(positions, client=client)

    assert payload.analysis_window.start_date is None
    assert payload.analysis_window.end_date is None
    assert payload.request_id.endswith("no-shared-window")


def test_build_portfolio_input_raises_when_any_fund_nav_is_missing():
    nav_by_code = {
        "000001": [
            {"date": "2026-01-01", "unit_net_value": "1.00"},
        ],
    }
    client = BackendFunctionClient(
        services=_portfolio_services(),
        transport=_portfolio_transport_factory(nav_by_code, failing_codes={"000002"}),
    )
    positions = [
        PortfolioPosition(code="000001", weight=0.5),
        PortfolioPosition(code="000002", weight=0.5),
    ]

    try:
        build_portfolio_input_from_backend_functions(positions, client=client)
    except ValueError as exc:
        assert "000002" in str(exc)
        assert "000001" not in str(exc)
    else:
        raise AssertionError("Expected ValueError for missing NAV data.")


def test_build_portfolio_input_degrades_gracefully_without_basic_info():
    nav_by_code = {
        "000001": [
            {"date": "2026-01-01", "unit_net_value": "1.00"},
            {"date": "2026-01-02", "unit_net_value": "1.02"},
        ],
    }

    def transport(method, url, payload, timeout):
        if "/functions" in url:
            if "market" in url:
                return {
                    "code": 200,
                    "data": [
                        {"name": "get_fund_hist", "path": "/hist", "method": "POST", "parameters": {}},
                        {"name": "get_fund_individual_basic_info", "path": "/basic", "method": "POST", "parameters": {}},
                    ],
                    "message": "success",
                }
            return {"code": 200, "data": [], "message": "success"}
        if url.endswith("/hist"):
            return {"code": 200, "data": nav_by_code.get((payload or {}).get("code", ""), [])}
        if url.endswith("/basic"):
            return {"code": 500, "data": None, "message": "basic info unavailable"}
        return {"code": 200, "data": []}

    client = BackendFunctionClient(services=_portfolio_services(), transport=transport)

    payload = build_portfolio_input_from_backend_functions(
        [PortfolioPosition(code="000001", weight=1.0, name="Fallback Name")],
        client=client,
    )

    assert payload.funds[0].fund_info.name == "Fallback Name"
    assert payload.funds[0].fund_info.category == "unknown"
    assert "get_fund_individual_basic_info" in payload.extra_context["errored_backend_tools"]


def test_news_registry_failure_degrades_instead_of_failing_analysis():
    # 新闻后端整个不可用（例如 403/未启动）时，market 数据仍应正常组装，
    # 新闻相关字段为空，由 SentimentAgent 输出 skipped，而不是整体 500。
    def transport(method, url, payload, timeout):
        if "/functions" in url:
            if "market" in url:
                return {
                    "code": 200,
                    "data": [
                        {"name": "get_fund_hist", "path": "/hist", "method": "POST", "parameters": {}},
                        {"name": "get_fund_individual_basic_info", "path": "/basic", "method": "POST", "parameters": {}},
                    ],
                    "message": "success",
                }
            raise BackendFunctionError("HTTP 403 from news functions registry")
        if url.endswith("/hist"):
            return {
                "code": 200,
                "data": [
                    {"date": "2026-01-01", "unit_net_value": "1.00"},
                    {"date": "2026-01-02", "unit_net_value": "1.02"},
                ],
            }
        if url.endswith("/basic"):
            return {"code": 200, "data": [{"fund_name": "Demo", "fund_type": "mixed"}]}
        return {"code": 200, "data": []}

    client = BackendFunctionClient(services=_portfolio_services(), transport=transport)

    payload = build_fund_input_from_backend_functions("000001", client=client)

    assert len(payload.nav_series) == 2
    assert payload.news_items == []
    assert "get_public_fund_announcement" in payload.extra_context["errored_backend_tools"]


def test_build_sector_view_funds_fetches_industry_and_degrades():
    def transport(method, url, payload, timeout):
        code = (payload or {}).get("code", "")
        if "/functions" in url:
            if "market" in url:
                return {
                    "code": 200,
                    "data": [
                        {"name": "get_fund_individual_basic_info", "path": "/basic", "method": "POST", "parameters": {}},
                        {"name": "get_fund_portfolio_industry_allocation", "path": "/industry", "method": "POST", "parameters": {}},
                    ],
                    "message": "success",
                }
            return {"code": 200, "data": [], "message": "success"}
        if url.endswith("/basic"):
            if code == "161725":
                return {"code": 200, "data": [{"fund_name": "白酒指数", "fund_type": "股票型-标准指数"}]}
            # 003358 基本信息失败，应降级为 unknown 类型而不是报错
            return {"code": 500, "data": None, "message": "basic unavailable"}
        if url.endswith("/industry"):
            if code == "161725":
                return {"code": 200, "data": [{"industry_category": "白酒", "pct": "94.34"}]}
            return {"code": 200, "data": []}
        return {"code": 200, "data": []}

    client = BackendFunctionClient(services=_portfolio_services(), transport=transport)

    funds, context = build_sector_view_funds_from_backend_functions(
        ["161725", "003358"], client=client
    )

    assert funds[0].fund_info.name == "白酒指数"
    assert funds[0].industry_exposure == {"白酒": 0.9434}
    assert funds[1].fund_info.category == "unknown"
    assert funds[1].industry_exposure == {}
    assert "get_fund_individual_basic_info" in context["errored_backend_tools"]
    assert context["data_source"] == "backend_function_registry"


class BackendFunctionClientRegressionTest(unittest.TestCase):
    def test_small_holding_percentages_are_run_by_unittest(self):
        test_build_fund_input_treats_small_holding_percentages_as_percent_units()

    def test_bond_holdings_and_asset_allocation_are_run_by_unittest(self):
        test_build_fund_input_maps_bond_holdings_and_asset_allocation()

    def test_start_date_filter_is_run_by_unittest(self):
        test_build_fund_input_applies_start_date_even_without_end_date()

    def test_explicit_start_date_window_is_not_truncated(self):
        test_build_fund_input_does_not_truncate_explicit_start_date_window()

    def test_latest_news_announcements_are_used(self):
        test_build_fund_input_uses_latest_news_announcements()

    def test_optional_bond_timeout_is_not_retried_across_years(self):
        test_optional_bond_timeout_is_not_retried_across_years()

    def test_portfolio_input_fetches_per_fund_data(self):
        test_build_portfolio_input_fetches_nav_and_basic_info_per_fund()

    def test_portfolio_input_disjoint_calendars_leave_window_empty(self):
        test_build_portfolio_input_with_disjoint_calendars_leaves_window_empty()

    def test_portfolio_input_fetches_lookthrough_data(self):
        test_build_portfolio_input_fetches_lookthrough_data_per_fund()

    def test_portfolio_input_can_skip_lookthrough(self):
        test_build_portfolio_input_can_skip_lookthrough_fetch()

    def test_sector_view_funds_fetch_and_degrade(self):
        test_build_sector_view_funds_fetches_industry_and_degrades()

    def test_news_registry_failure_degrades(self):
        test_news_registry_failure_degrades_instead_of_failing_analysis()

    def test_portfolio_input_raises_on_missing_nav(self):
        test_build_portfolio_input_raises_when_any_fund_nav_is_missing()

    def test_portfolio_input_degrades_without_basic_info(self):
        test_build_portfolio_input_degrades_gracefully_without_basic_info()


if __name__ == "__main__":
    unittest.main()
