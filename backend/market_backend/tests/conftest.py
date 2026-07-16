import os
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

# Prevent the cache scheduler from starting during test runs.
# Must be set BEFORE importing app.
os.environ["MARKET_TESTING"] = "1"

from app import create_app


@pytest.fixture(autouse=True)
def _disable_cache(monkeypatch):
    """Make CacheDao always return None (cache miss) during tests so
    mocks on the API layer are exercised."""
    from daos.cache_dao import CacheDao
    monkeypatch.setattr(CacheDao, "get", lambda *a, **kw: None)
    monkeypatch.setattr(CacheDao, "get_df", lambda *a, **kw: None)
    monkeypatch.setattr(CacheDao, "set", lambda *a, **kw: False)
    monkeypatch.setattr(CacheDao, "set_df", lambda *a, **kw: False)
    monkeypatch.setattr(CacheDao, "exists", lambda *a, **kw: False)


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Sample DataFrames for mocking API returns
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_stock_spot_df():
    return pd.DataFrame([
        {
            "stock_code": "000001", "stock_name": "平安银行", "latest_price": 12.50,
            "change_pct": 2.5, "change_amount": 0.30, "volume": 50000000,
            "turnover": 625000000, "high": 12.80, "low": 12.10,
            "open": 12.20, "prev_close": 12.20, "amplitude": 5.74,
            "volume_ratio": 1.2, "turnover_rate": 0.8,
            "pe_dynamic": 8.5, "pb": 1.1, "total_market_cap": 300000000000,
            "circulating_market_cap": 280000000000,
        },
        {
            "stock_code": "000002", "stock_name": "万科A", "latest_price": 15.30,
            "change_pct": -1.2, "change_amount": -0.19, "volume": 30000000,
            "turnover": 459000000, "high": 15.80, "low": 15.10,
            "open": 15.49, "prev_close": 15.49, "amplitude": 4.52,
            "volume_ratio": 0.9, "turnover_rate": 0.5,
            "pe_dynamic": 10.2, "pb": 0.9, "total_market_cap": 180000000000,
            "circulating_market_cap": 170000000000,
        },
    ])


@pytest.fixture
def sample_stock_hist_df():
    return pd.DataFrame([
        {"date": "2026-05-20", "stock_code": "000001", "stock_name": "平安银行",
         "open": 12.00, "close": 12.50, "high": 12.80, "low": 11.90,
         "volume": 50000000, "turnover": 620000000, "amplitude": 7.5,
         "change_pct": 3.2, "change_amount": 0.39, "turnover_rate": 0.8},
        {"date": "2026-05-21", "stock_code": "000001", "stock_name": "平安银行",
         "open": 12.50, "close": 12.30, "high": 12.70, "low": 12.20,
         "volume": 45000000, "turnover": 560000000, "amplitude": 4.0,
         "change_pct": -1.6, "change_amount": -0.20, "turnover_rate": 0.7},
    ])


@pytest.fixture
def sample_bid_ask_df():
    return pd.DataFrame([
        {"latest_price": 12.50, "average_price": 12.45, "change_pct": 2.5,
         "change_amount": 0.30, "total_volume": 50000000, "turnover": 625000000,
         "turnover_rate": 0.8, "volume_ratio": 1.2, "high": 12.80, "low": 12.10,
         "open": 12.20, "prev_close": 12.20, "upper_limit": 13.42,
         "lower_limit": 10.98, "bid_volume": 26000000, "ask_volume": 24000000},
    ])


@pytest.fixture
def sample_fund_etf_spot_df():
    return pd.DataFrame([
        {"fund_code": "510050", "fund_name": "华夏上证50ETF", "latest_price": 2.850,
         "change_pct": 1.5, "change_amount": 0.042, "volume": 100000000,
         "turnover": 285000000, "high": 2.880, "low": 2.810,
         "open": 2.808, "prev_close": 2.808, "iopv": 2.848,
         "discount_rate": 0.07, "turnover_rate": 2.5, "volume_ratio": 1.1,
         "order_ratio": 0.5, "current_volume": 1000},
        {"fund_code": "510300", "fund_name": "沪深300ETF", "latest_price": 4.120,
         "change_pct": -0.5, "change_amount": -0.021, "volume": 80000000,
         "turnover": 329600000, "high": 4.200, "low": 4.100,
         "open": 4.141, "prev_close": 4.141, "iopv": 4.118,
         "discount_rate": 0.05, "turnover_rate": 2.0, "volume_ratio": 0.9,
         "order_ratio": -0.3, "current_volume": 800},
    ])


@pytest.fixture
def sample_fund_name_list_df():
    return pd.DataFrame([
        {"fund_code": "510050", "pinyin_abbr": "HXSBETF", "fund_name": "华夏上证50ETF",
         "fund_type": "ETF", "pinyin_full": "huaxiashangzheng50ETF"},
        {"fund_code": "510300", "pinyin_abbr": "HS300ETF", "fund_name": "沪深300ETF",
         "fund_type": "ETF", "pinyin_full": "hushen300ETF"},
    ])


@pytest.fixture
def sample_crypto_books():
    return {
        "bids": [[96500.5, 0.5], [96500.0, 1.2], [96490.0, 2.0]],
        "asks": [[96550.0, 0.8], [96560.0, 1.5], [96570.0, 0.3]],
    }


@pytest.fixture
def sample_crypto_ticker():
    return {
        "symbol": "BTC-USDT",
        "last_price": 96520.5,
        "high24h": 97500.0,
        "low24h": 95800.0,
        "volume24h": 15000.5,
        "change_percent": 0.0125,
    }


@pytest.fixture
def sample_crypto_klines():
    return [
        {"start_time": 1716854400000, "open_price": 96500.0, "high_price": 96600.0,
         "low_price": 96400.0, "close_price": 96550.0, "volume": 100.5,
         "volume_currency": 9700000.0},
        {"start_time": 1716854460000, "open_price": 96550.0, "high_price": 96700.0,
         "low_price": 96500.0, "close_price": 96620.0, "volume": 120.3,
         "volume_currency": 11620000.0},
    ]


@pytest.fixture
def sample_crypto_ma():
    return {
        "symbol": "BTC-USDT",
        "interval": "1m",
        "ma_periods": [5, 10],
        "items": [
            {"datetime": 1716854400000, "close_price": 96550.0, "ma": [None, None]},
            {"datetime": 1716854460000, "close_price": 96620.0, "ma": [96585.0, None]},
        ],
    }


# ---------------------------------------------------------------------------
# Sample DataFrames for individual_basic_info (raw akshare return: item/value format)
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_fund_individual_basic_info_raw_df():
    """Simulates raw ak.fund_individual_basic_info_xq() return with item/value columns.
    The API transposes this (set_index('item').T), then maps Chinese→English columns."""
    return pd.DataFrame([
        {"item": "基金代码", "value": "000001"},
        {"item": "基金名称", "value": "华夏成长混合"},
        {"item": "成立时间", "value": "20010921"},
        {"item": "最新规模", "value": "85.6亿"},
        {"item": "基金公司", "value": "华夏基金管理有限公司"},
        {"item": "基金经理", "value": "张三"},
        {"item": "托管银行", "value": "中国银行"},
        {"item": "基金类型", "value": "混合型"},
        {"item": "评级机构", "value": "晨星"},
        {"item": "基金评级", "value": "★★★★★"},
        {"item": "投资策略", "value": "稳健增长策略"},
        {"item": "投资目标", "value": "长期资本增值"},
    ])


# ---------------------------------------------------------------------------
# Sample DataFrames for individual_basic_info (mapped, after API transposes & renames)
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_fund_individual_basic_info_mapped_df():
    """Simulates AksharePublicFund.get_fund_individual_basic_info() return."""
    return pd.DataFrame([{
        "fund_code": "000001",
        "fund_name": "华夏成长混合",
        "inception_date": "20010921",
        "latest_aum": "85.6亿",
        "fund_company": "华夏基金管理有限公司",
        "fund_manager": "张三",
        "custodian_bank": "中国银行",
        "fund_type": "混合型",
        "rating_agency": "晨星",
        "fund_rating": "★★★★★",
        "investment_strategy": "稳健增长策略",
        "investment_objective": "长期资本增值",
    }])


# ---------------------------------------------------------------------------
# Sample DataFrames for individual_detail_hold
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_fund_individual_detail_hold_raw_df():
    """Simulates raw ak.fund_individual_detail_hold_xq() return."""
    return pd.DataFrame([
        {"资产类型": "股票", "仓位占比": "65.80%"},
        {"资产类型": "债券", "仓位占比": "25.30%"},
        {"资产类型": "现金", "仓位占比": "8.90%"},
    ])


@pytest.fixture
def sample_fund_individual_detail_hold_mapped_df():
    """Simulates AksharePublicFund.get_fund_individual_detail_hold() return."""
    return pd.DataFrame([
        {"asset_type": "股票", "pct": "65.80%"},
        {"asset_type": "债券", "pct": "25.30%"},
        {"asset_type": "现金", "pct": "8.90%"},
    ])


# ---------------------------------------------------------------------------
# Sample DataFrames for portfolio_industry_allocation
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_portfolio_industry_allocation_raw_df():
    """Simulates raw ak.fund_portfolio_industry_allocation_em() return.
    Contains two '截止日期' groups; the API filters to the first date only."""
    return pd.DataFrame([
        {"截止时间": "2025Q4", "序号": 1, "行业类别": "制造业", "占净值比例": "45.20", "市值": "38.7亿"},
        {"截止时间": "2025Q4", "序号": 2, "行业类别": "金融业", "占净值比例": "20.10", "市值": "17.2亿"},
        {"截止时间": "2025Q3", "序号": 1, "行业类别": "制造业", "占净值比例": "42.80", "市值": "36.5亿"},
    ])


@pytest.fixture
def sample_portfolio_industry_allocation_mapped_df():
    """Simulates AksharePublicFund.get_fund_portfolio_industry_allocation_em() return
    (filtered to first date only, English column names)."""
    return pd.DataFrame([
        {"sequence": 1, "industry_category": "制造业", "pct": "45.20",
         "market_value": "38.7亿", "as_of_date": "2025Q4"},
        {"sequence": 2, "industry_category": "金融业", "pct": "20.10",
         "market_value": "17.2亿", "as_of_date": "2025Q4"},
    ])


# ---------------------------------------------------------------------------
# Sample DataFrames for portfolio_hold_stock
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_portfolio_hold_stock_raw_df():
    """Simulates raw ak.fund_portfolio_hold_em() return for stocks."""
    return pd.DataFrame([
        {"截止时间": "2025Q4", "序号": 1, "股票代码": "600519", "股票名称": "贵州茅台",
         "占净值比例": "9.85", "持股数": "120.5万", "持仓市值": "21.6亿", "季度": "2025Q4"},
        {"截止时间": "2025Q4", "序号": 2, "股票代码": "000858", "股票名称": "五粮液",
         "占净值比例": "7.52", "持股数": "200.0万", "持仓市值": "16.5亿", "季度": "2025Q4"},
        {"截止时间": "2025Q3", "序号": 1, "股票代码": "600519", "股票名称": "贵州茅台",
         "占净值比例": "9.20", "持股数": "118.0万", "持仓市值": "20.1亿", "季度": "2025Q3"},
    ])


@pytest.fixture
def sample_portfolio_hold_stock_mapped_df():
    """Simulates AksharePublicFund.get_fund_portfolio_hold_stock() return."""
    return pd.DataFrame([
        {"sequence": 1, "stock_code": "600519", "stock_name": "贵州茅台",
         "pct": "9.85", "hold_shares": "120.5万", "hold_market_value": "21.6亿",
         "quarter": "2025Q4"},
        {"sequence": 2, "stock_code": "000858", "stock_name": "五粮液",
         "pct": "7.52", "hold_shares": "200.0万", "hold_market_value": "16.5亿",
         "quarter": "2025Q4"},
    ])


# ---------------------------------------------------------------------------
# Sample DataFrames for portfolio_hold_bond
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_portfolio_hold_bond_raw_df():
    """Simulates raw ak.fund_portfolio_bond_hold_em() return."""
    return pd.DataFrame([
        {"截止时间": "2025Q4", "序号": 1, "债券代码": "200210", "债券名称": "20国开10",
         "占净值比例": "5.20", "持仓市值": "4.45亿", "季度": "2025Q4"},
        {"截止时间": "2025Q4", "序号": 2, "债券代码": "210203", "债券名称": "21国开03",
         "占净值比例": "3.80", "持仓市值": "3.25亿", "季度": "2025Q4"},
        {"截止时间": "2025Q3", "序号": 1, "债券代码": "200210", "债券名称": "20国开10",
         "占净值比例": "5.50", "持仓市值": "4.70亿", "季度": "2025Q3"},
    ])


@pytest.fixture
def sample_portfolio_hold_bond_mapped_df():
    """Simulates AksharePublicFund.get_fund_portfolio_hold_bond() return."""
    return pd.DataFrame([
        {"sequence": 1, "bond_code": "200210", "bond_name": "20国开10",
         "pct": "5.20", "hold_market_value": "4.45亿", "quarter": "2025Q4"},
        {"sequence": 2, "bond_code": "210203", "bond_name": "21国开03",
         "pct": "3.80", "hold_market_value": "3.25亿", "quarter": "2025Q4"},
    ])
