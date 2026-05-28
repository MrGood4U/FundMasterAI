import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

from app import create_app


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
