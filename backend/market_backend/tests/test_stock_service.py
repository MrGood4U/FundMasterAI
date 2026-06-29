import pytest
from unittest.mock import MagicMock, patch

from services.stock_service import StockService


@pytest.fixture
def service():
    return StockService()


class TestGetAllASpot:
    def test_returns_records_for_eastmoney(self, service, sample_stock_spot_df):
        service.akapi.a_spot_all = MagicMock(return_value=sample_stock_spot_df)
        result = service.get_all_a_spot("eastmoney")
        assert len(result) == 2
        assert result[0]["stock_code"] == "000001"
        assert result[1]["stock_code"] == "000002"

    def test_returns_none_for_unsupported_platform(self, service):
        service.akapi.a_spot_all = MagicMock(return_value=None)
        result = service.get_all_a_spot("unknown")
        assert result is None

    def test_returns_empty_list_for_empty_dataframe(self, service):
        import pandas as pd
        service.akapi.a_spot_all = MagicMock(return_value=pd.DataFrame())
        result = service.get_all_a_spot("eastmoney")
        assert result == []


class TestGetASpot:
    def test_returns_single_record(self, service, sample_stock_spot_df):
        single = sample_stock_spot_df.iloc[[0]]
        service.akapi.a_spot_one = MagicMock(return_value=single)
        result = service.get_a_spot("eastmoney", "000001", None)
        assert len(result) == 1
        assert result[0]["stock_code"] == "000001"

    def test_returns_none_for_unsupported_platform(self, service):
        service.akapi.a_spot_one = MagicMock(return_value=None)
        result = service.get_a_spot("unknown", "000001", None)
        assert result is None

    def test_passes_name_to_api(self, service, sample_stock_spot_df):
        single = sample_stock_spot_df.iloc[[0]]
        service.akapi.a_spot_one = MagicMock(return_value=single)
        result = service.get_a_spot("eastmoney", None, "平安银行")
        service.akapi.a_spot_one.assert_called_once_with("eastmoney", None, "平安银行")
        assert len(result) == 1


class TestGetAHist:
    def test_returns_records_for_eastmoney(self, service, sample_stock_hist_df):
        service.akapi.a_hist = MagicMock(return_value=sample_stock_hist_df)
        result = service.get_a_hist("eastmoney", "000001", "daily",
                                     "2026-05-20", "2026-05-21", "qfq")
        assert len(result) == 2
        assert result[0]["date"] == "2026-05-20"

    def test_returns_records_for_sina(self, service, sample_stock_hist_df):
        service.akapi.a_hist = MagicMock(return_value=sample_stock_hist_df)
        result = service.get_a_hist("sina", "000001", "daily",
                                     "2026-05-20", "2026-05-21", "qfq")
        assert len(result) == 2

    def test_returns_none_for_unsupported_platform(self, service):
        service.akapi.a_hist = MagicMock(return_value=None)
        result = service.get_a_hist("unknown", "000001", "daily",
                                     "2026-05-20", "2026-05-21", "qfq")
        assert result is None


class TestGetABidAsk:
    def test_returns_records_for_eastmoney(self, service, sample_bid_ask_df):
        service.akapi.a_bid_ask = MagicMock(return_value=sample_bid_ask_df)
        result = service.get_a_bid_ask("eastmoney", "000001")
        assert len(result) == 1
        assert result[0]["latest_price"] == 12.50

    def test_returns_none_for_unsupported_platform(self, service):
        service.akapi.a_bid_ask = MagicMock(return_value=None)
        result = service.get_a_bid_ask("unknown", "000001")
        assert result is None
