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
        result, errmsg = service.get_one_real_time(None, "510050", "eastmoney", "ETF")
        assert errmsg is None
        assert len(result) == 1
        assert result[0]["fund_code"] == "510050"

    def test_filters_by_name(self, service, sample_fund_etf_spot_df):
        service.akapi.real_time = MagicMock(return_value=sample_fund_etf_spot_df)
        result, errmsg = service.get_one_real_time("华夏上证50ETF", None, "eastmoney", "ETF")
        assert errmsg is None
        assert len(result) == 1
        assert result[0]["fund_name"] == "华夏上证50ETF"

    def test_filters_by_fund_name_key(self, service):
        df = pd.DataFrame([{"fund_code": "510050", "fund_name": "测试基金"}])
        service.akapi.real_time = MagicMock(return_value=df)
        result, errmsg = service.get_one_real_time("测试基金", None, "eastmoney", "ETF")
        assert errmsg is None
        assert len(result) == 1

    def test_returns_empty_list_when_no_match(self, service, sample_fund_etf_spot_df):
        service.akapi.real_time = MagicMock(return_value=sample_fund_etf_spot_df)
        result, errmsg = service.get_one_real_time(None, "999999", "eastmoney", "ETF")
        assert result == []
        assert errmsg is not None


class TestGetAllRealTime:
    def test_returns_all_records(self, service, sample_fund_etf_spot_df):
        service.akapi.real_time = MagicMock(return_value=sample_fund_etf_spot_df)
        result = service.get_all_real_time("eastmoney", "ETF")
        assert len(result) == 2

    def test_passes_platform_and_symbol(self, service, sample_fund_etf_spot_df):
        service.akapi.real_time = MagicMock(return_value=sample_fund_etf_spot_df)
        service.get_all_real_time("tonghuashun", "ETF")
        # tonghuashun always fetches "all" to keep the shared cache complete,
        # then filters by fund_type client-side.
        service.akapi.real_time.assert_called_once_with("all", "tonghuashun")


class TestGetHist:
    def test_returns_records(self, service, sample_stock_hist_df):
        service.efapi.hist = MagicMock(return_value=sample_stock_hist_df)
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


class TestGetFundIndividualBasicInfo:
    def test_returns_list_of_dicts(self, service, sample_fund_individual_basic_info_mapped_df):
        service.akapi.get_fund_individual_basic_info = MagicMock(
            return_value=sample_fund_individual_basic_info_mapped_df)
        result = service.get_fund_individual_basic_info("000001")

        service.akapi.get_fund_individual_basic_info.assert_called_once_with("000001")
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["fund_code"] == "000001"
        assert result[0]["fund_name"] == "华夏成长混合"
        assert result[0]["fund_company"] == "华夏基金管理有限公司"

    def test_returns_empty_list_when_none(self, service):
        service.akapi.get_fund_individual_basic_info = MagicMock(return_value=None)
        result = service.get_fund_individual_basic_info("000001")
        assert result == []

    def test_returns_empty_list_when_empty_df(self, service):
        service.akapi.get_fund_individual_basic_info = MagicMock(return_value=pd.DataFrame())
        result = service.get_fund_individual_basic_info("000001")
        assert result == []


class TestGetFundIndividualDetailHold:
    def test_returns_list_of_dicts(self, service, sample_fund_individual_detail_hold_mapped_df):
        service.akapi.get_fund_individual_detail_hold = MagicMock(
            return_value=sample_fund_individual_detail_hold_mapped_df)
        result = service.get_fund_individual_detail_hold("000001", "20260604")

        service.akapi.get_fund_individual_detail_hold.assert_called_once_with("000001", "20260604")
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]["asset_type"] == "股票"
        assert result[0]["pct"] == "65.80%"

    def test_returns_empty_list_when_empty(self, service):
        service.akapi.get_fund_individual_detail_hold = MagicMock(return_value=pd.DataFrame())
        result = service.get_fund_individual_detail_hold("000001", "20260604")
        assert result == []


class TestGetFundPortfolioIndustryAllocationEm:
    def test_returns_list_of_dicts(self, service, sample_portfolio_industry_allocation_mapped_df):
        service.akapi.get_fund_portfolio_industry_allocation_em = MagicMock(
            return_value=sample_portfolio_industry_allocation_mapped_df)
        result = service.get_fund_portfolio_industry_allocation_em("000001", "2025")

        service.akapi.get_fund_portfolio_industry_allocation_em.assert_called_once_with("000001", "2025")
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["industry_category"] == "制造业"
        assert result[0]["pct"] == "45.20"

    def test_returns_empty_list_when_none(self, service):
        service.akapi.get_fund_portfolio_industry_allocation_em = MagicMock(return_value=None)
        result = service.get_fund_portfolio_industry_allocation_em("000001", "2025")
        assert result == []

    def test_returns_empty_list_when_empty_list(self, service):
        """API returns [] (Python list) when no data — service should also return []."""
        service.akapi.get_fund_portfolio_industry_allocation_em = MagicMock(return_value=[])
        result = service.get_fund_portfolio_industry_allocation_em("000001", "2025")
        assert result == []


class TestGetFundPortfolioHoldStock:
    def test_returns_list_of_dicts(self, service, sample_portfolio_hold_stock_mapped_df):
        service.akapi.get_fund_portfolio_hold_stock = MagicMock(
            return_value=sample_portfolio_hold_stock_mapped_df)
        result = service.get_fund_portfolio_hold_stock("000001", "2025")

        service.akapi.get_fund_portfolio_hold_stock.assert_called_once_with("000001", "2025")
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["stock_code"] == "600519"
        assert result[0]["stock_name"] == "贵州茅台"
        assert result[0]["pct"] == "9.85"

    def test_returns_empty_list_when_none(self, service):
        service.akapi.get_fund_portfolio_hold_stock = MagicMock(return_value=None)
        result = service.get_fund_portfolio_hold_stock("000001", "2025")
        assert result == []

    def test_returns_empty_list_when_empty_list(self, service):
        service.akapi.get_fund_portfolio_hold_stock = MagicMock(return_value=[])
        result = service.get_fund_portfolio_hold_stock("000001", "2025")
        assert result == []


class TestGetFundPortfolioHoldBond:
    def test_returns_list_of_dicts(self, service, sample_portfolio_hold_bond_mapped_df):
        service.akapi.get_fund_portfolio_hold_bond = MagicMock(
            return_value=sample_portfolio_hold_bond_mapped_df)
        result = service.get_fund_portfolio_hold_bond("000001", "2025")

        service.akapi.get_fund_portfolio_hold_bond.assert_called_once_with("000001", "2025")
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["bond_code"] == "200210"
        assert result[0]["bond_name"] == "20国开10"
        assert result[0]["pct"] == "5.20"

    def test_returns_empty_list_when_none(self, service):
        service.akapi.get_fund_portfolio_hold_bond = MagicMock(return_value=None)
        result = service.get_fund_portfolio_hold_bond("000001", "2025")
        assert result == []

    def test_returns_empty_list_when_empty_list(self, service):
        service.akapi.get_fund_portfolio_hold_bond = MagicMock(return_value=[])
        result = service.get_fund_portfolio_hold_bond("000001", "2025")
        assert result == []
