import pandas as pd
import pytest

from apis.field_mapping import (
    apply_mapping,
    STOCK_SPOT_EM_MAP,
    STOCK_HIST_EM_MAP,
    BID_ASK_EM_MAP,
    FUND_ETF_SPOT_EM_MAP,
    FUND_LOF_SPOT_EM_MAP,
    FUND_HIST_EM_MAP,
    FUND_HIST_MIN_EM_MAP,
    FUND_CATEGORY_THS_MAP,
    FUND_SPOT_SINA_MAP,
    FUND_NAME_EM_MAP,
)


class TestApplyMapping:
    def test_renames_matching_columns(self):
        df = pd.DataFrame([{"最新价": 12.50, "涨跌幅": 2.5}])
        result = apply_mapping(df, {"最新价": "latest_price", "涨跌幅": "change_pct"})
        assert list(result.columns) == ["latest_price", "change_pct"]
        assert result.iloc[0]["latest_price"] == 12.50
        assert result.iloc[0]["change_pct"] == 2.5

    def test_ignores_missing_columns(self):
        df = pd.DataFrame([{"最新价": 12.50}])
        result = apply_mapping(df, {"最新价": "latest_price", "不存在的列": "nonexistent"})
        assert list(result.columns) == ["latest_price"]

    def test_columns_not_in_mapping_pass_through(self):
        df = pd.DataFrame([{"最新价": 12.50, "extra_column": 42}])
        result = apply_mapping(df, {"最新价": "latest_price"})
        assert "extra_column" in result.columns
        assert result.iloc[0]["extra_column"] == 42

    def test_empty_mapping_returns_same_df(self):
        df = pd.DataFrame([{"a": 1, "b": 2}])
        result = apply_mapping(df, {})
        pd.testing.assert_frame_equal(result, df)

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        result = apply_mapping(df, {"最新价": "latest_price"})
        assert result.empty


class TestStockSpotEmMap:
    def test_renames_code_and_name(self):
        df = pd.DataFrame([{"代码": "000001", "名称": "平安银行"}])
        result = apply_mapping(df, STOCK_SPOT_EM_MAP)
        assert "stock_code" in result.columns
        assert "stock_name" in result.columns

    def test_renames_price_fields(self):
        df = pd.DataFrame([{"最新价": 10.0, "涨跌幅": 1.5, "成交量": 1000}])
        result = apply_mapping(df, STOCK_SPOT_EM_MAP)
        assert result.iloc[0]["latest_price"] == 10.0
        assert result.iloc[0]["change_pct"] == 1.5
        assert result.iloc[0]["volume"] == 1000


class TestFundMappings:
    def test_etf_spot_map_renames_fund_code(self):
        df = pd.DataFrame([{"基金代码": "510050", "IOPV实时估值": 2.85}])
        result = apply_mapping(df, FUND_ETF_SPOT_EM_MAP)
        assert "fund_code" in result.columns
        assert result.iloc[0]["iopv"] == 2.85

    def test_lof_spot_map_renames_fund_code(self):
        df = pd.DataFrame([{"基金代码": "160505", "最新价": 1.50}])
        result = apply_mapping(df, FUND_LOF_SPOT_EM_MAP)
        assert "fund_code" in result.columns
        assert result.iloc[0]["latest_price"] == 1.50

    def test_fund_name_em_map(self):
        df = pd.DataFrame([{"基金代码": "510050", "拼音缩写": "HXSB", "基金简称": "华夏上证50ETF"}])
        result = apply_mapping(df, FUND_NAME_EM_MAP)
        assert "fund_code" in result.columns
        assert "pinyin_abbr" in result.columns
        assert "fund_name" in result.columns
