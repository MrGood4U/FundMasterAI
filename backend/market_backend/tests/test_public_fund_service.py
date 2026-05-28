import pytest
from unittest.mock import MagicMock
import pandas as pd

from services.public_fund_service import PublicFundService


@pytest.fixture
def service():
    return PublicFundService()


class TestGetOneRealTime:
    def test_filters_by_code(self, service, sample_fund_etf_spot_df):
        service.akapi.real_time = MagicMock(return_value=sample_fund_etf_spot_df)
        result = service.get_one_real_time(None, "510050", "eastmoney", "ETF")
        assert len(result) == 1
        assert result[0]["fund_code"] == "510050"

    def test_filters_by_name(self, service, sample_fund_etf_spot_df):
        service.akapi.real_time = MagicMock(return_value=sample_fund_etf_spot_df)
        result = service.get_one_real_time("华夏上证50ETF", None, "eastmoney", "ETF")
        assert len(result) == 1
        assert result[0]["fund_name"] == "华夏上证50ETF"

    def test_filters_by_fund_name_key(self, service):
        df = pd.DataFrame([{"fund_code": "510050", "fund_name": "测试基金"}])
        service.akapi.real_time = MagicMock(return_value=df)
        result = service.get_one_real_time("测试基金", None, "eastmoney", "ETF")
        assert len(result) == 1

    def test_returns_empty_list_when_no_match(self, service, sample_fund_etf_spot_df):
        service.akapi.real_time = MagicMock(return_value=sample_fund_etf_spot_df)
        result = service.get_one_real_time(None, "999999", "eastmoney", "ETF")
        assert result == []


class TestGetAllRealTime:
    def test_returns_all_records(self, service, sample_fund_etf_spot_df):
        service.akapi.real_time = MagicMock(return_value=sample_fund_etf_spot_df)
        result = service.get_all_real_time("eastmoney", "ETF")
        assert len(result) == 2

    def test_passes_platform_and_symbol(self, service, sample_fund_etf_spot_df):
        service.akapi.real_time = MagicMock(return_value=sample_fund_etf_spot_df)
        service.get_all_real_time("tonghuashun", "ETF")
        service.akapi.real_time.assert_called_once_with("ETF", "tonghuashun")


class TestGetHist:
    def test_returns_records(self, service, sample_stock_hist_df):
        service.akapi.hist = MagicMock(return_value=sample_stock_hist_df)
        result = service.get_hist("ETF", "eastmoney", "510050",
                                   "2026-05-20", "2026-05-21", "daily", "qfq")
        assert len(result) == 2


class TestGetHistMin:
    def test_returns_records(self, service, sample_stock_hist_df):
        service.akapi.hist_min = MagicMock(return_value=sample_stock_hist_df)
        result = service.get_hist_min("ETF", "eastmoney", "510050",
                                       "2026-05-20", "2026-05-21", "5", "qfq")
        assert len(result) == 2


class TestGetFundNameList:
    def test_returns_records(self, service, sample_fund_name_list_df):
        service.akapi.get_fund_name_list = MagicMock(return_value=sample_fund_name_list_df)
        result = service.get_fund_name_list()
        assert len(result) == 2
        assert result[0]["fund_code"] == "510050"
