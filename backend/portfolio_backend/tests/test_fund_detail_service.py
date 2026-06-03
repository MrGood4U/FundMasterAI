import pytest
from unittest.mock import MagicMock, patch

from services.fund_detail_service import FundDetailService


@pytest.fixture
def service():
    """Return a FundDetailService with MarketClient mocked."""
    svc = FundDetailService()
    svc.client = MagicMock()
    return svc


class TestGetDetailHold:
    def test_returns_data_from_client(self, service):
        service.client.get_fund_detail_hold.return_value = [
            {"asset_type": "股票", "pct": 72.35},
            {"asset_type": "债券", "pct": 18.20},
        ]
        result = service.get_detail_hold("000001", "20241231")

        service.client.get_fund_detail_hold.assert_called_once_with("000001", "20241231")
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["asset_type"] == "股票"
        assert result[1]["pct"] == 18.20

    def test_returns_none_when_client_returns_none(self, service):
        service.client.get_fund_detail_hold.return_value = None
        result = service.get_detail_hold("999999")
        assert result is None

    def test_passes_none_date_by_default(self, service):
        service.client.get_fund_detail_hold.return_value = []
        service.get_detail_hold("000001")
        service.client.get_fund_detail_hold.assert_called_once_with("000001", None)


class TestGetIndustryAllocation:
    def test_returns_data_from_client(self, service):
        service.client.get_fund_industry_allocation.return_value = [
            {"sequence": 1, "industry_category": "制造业", "pct": 35.42,
             "market_value": 1250000000, "as_of_date": "2025Q1"},
        ]
        result = service.get_industry_allocation("000001", "2025")

        service.client.get_fund_industry_allocation.assert_called_once_with("000001", "2025")
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["industry_category"] == "制造业"
        assert result[0]["pct"] == 35.42

    def test_returns_none_when_client_returns_none(self, service):
        service.client.get_fund_industry_allocation.return_value = None
        result = service.get_industry_allocation("999999")
        assert result is None

    def test_passes_none_year_by_default(self, service):
        service.client.get_fund_industry_allocation.return_value = []
        service.get_industry_allocation("000001")
        service.client.get_fund_industry_allocation.assert_called_once_with("000001", None)


class TestGetStockHolds:
    def test_returns_data_from_client(self, service):
        service.client.get_fund_stock_holds.return_value = [
            {"sequence": 1, "stock_code": "600519", "stock_name": "贵州茅台",
             "pct": 8.52, "hold_shares": 120000, "hold_market_value": 210000000,
             "quarter": "2025Q1"},
        ]
        result = service.get_stock_holds("000001", "2025")

        service.client.get_fund_stock_holds.assert_called_once_with("000001", "2025")
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["stock_code"] == "600519"
        assert result[0]["stock_name"] == "贵州茅台"

    def test_returns_none_when_client_returns_none(self, service):
        service.client.get_fund_stock_holds.return_value = None
        result = service.get_stock_holds("999999")
        assert result is None

    def test_passes_none_year_by_default(self, service):
        service.client.get_fund_stock_holds.return_value = []
        service.get_stock_holds("000001")
        service.client.get_fund_stock_holds.assert_called_once_with("000001", None)


class TestGetBondHolds:
    def test_returns_data_from_client(self, service):
        service.client.get_fund_bond_holds.return_value = [
            {"sequence": 1, "bond_code": "230016", "bond_name": "23附息国债16",
             "pct": 5.10, "hold_market_value": 85000000, "quarter": "2025Q1"},
        ]
        result = service.get_bond_holds("000001", "2025")

        service.client.get_fund_bond_holds.assert_called_once_with("000001", "2025")
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["bond_code"] == "230016"
        assert result[0]["bond_name"] == "23附息国债16"

    def test_returns_none_when_client_returns_none(self, service):
        service.client.get_fund_bond_holds.return_value = None
        result = service.get_bond_holds("999999")
        assert result is None

    def test_passes_none_year_by_default(self, service):
        service.client.get_fund_bond_holds.return_value = []
        service.get_bond_holds("000001")
        service.client.get_fund_bond_holds.assert_called_once_with("000001", None)
