import json
from unittest.mock import MagicMock, patch

import pytest

from apis.market_client import MarketClient


@pytest.fixture
def client():
    """Return a fresh MarketClient for each test."""
    return MarketClient()


def _mock_response(code=200, data=None):
    """Build a MagicMock that behaves like a requests.Response with .json()."""
    resp = MagicMock()
    resp.json.return_value = {"code": code, "data": data, "message": "success"}
    return resp


# ---------------------------------------------------------------------------
# get_fund_detail_hold
# ---------------------------------------------------------------------------


class TestGetFundDetailHold:
    def test_returns_data_on_success(self, client):
        mock_resp = _mock_response(code=200, data=[
            {"asset_type": "股票", "pct": 72.35},
            {"asset_type": "债券", "pct": 18.20},
        ])
        with patch("apis.market_client.requests.post", return_value=mock_resp) as mock_post:
            result = client.get_fund_detail_hold("000001", "20241231")

        mock_post.assert_called_once_with(
            f"{client.base_url}/api/market/fund_public/individual_detail_hold",
            json={"code": "000001", "date": "20241231"},
            timeout=5,
        )
        assert result == [{"asset_type": "股票", "pct": 72.35}, {"asset_type": "债券", "pct": 18.20}]

    def test_returns_none_when_code_not_200(self, client):
        mock_resp = _mock_response(code=500, data=None)
        with patch("apis.market_client.requests.post", return_value=mock_resp):
            result = client.get_fund_detail_hold("000001", "20241231")
        assert result is None

    def test_returns_none_on_connection_error(self, client):
        with patch("apis.market_client.requests.post", side_effect=ConnectionError):
            result = client.get_fund_detail_hold("000001", "20241231")
        assert result is None

    def test_fills_default_date_when_none(self, client):
        mock_resp = _mock_response(code=200, data=[])
        with patch("apis.market_client.requests.post", return_value=mock_resp) as mock_post:
            client.get_fund_detail_hold("000001", None)

        call_args = mock_post.call_args[1]["json"]
        assert call_args["code"] == "000001"
        # When date is None, it fills with today's date (YYYYmmdd)
        assert "date" in call_args
        assert len(call_args["date"]) == 8


# ---------------------------------------------------------------------------
# get_fund_industry_allocation
# ---------------------------------------------------------------------------


class TestGetFundIndustryAllocation:
    def test_returns_data_on_success(self, client):
        mock_resp = _mock_response(code=200, data=[
            {"sequence": 1, "industry_category": "制造业", "pct": 35.42,
             "market_value": 1250000000, "as_of_date": "2025Q1"},
        ])
        with patch("apis.market_client.requests.post", return_value=mock_resp) as mock_post:
            result = client.get_fund_industry_allocation("000001", "2025")

        mock_post.assert_called_once_with(
            f"{client.base_url}/api/market/fund_public/portfolio_industry_allocation",
            json={"code": "000001", "year": "2025"},
            timeout=5,
        )
        assert len(result) == 1
        assert result[0]["industry_category"] == "制造业"

    def test_returns_none_when_code_not_200(self, client):
        mock_resp = _mock_response(code=404, data=None)
        with patch("apis.market_client.requests.post", return_value=mock_resp):
            result = client.get_fund_industry_allocation("000001", "2025")
        assert result is None

    def test_returns_none_on_connection_error(self, client):
        with patch("apis.market_client.requests.post", side_effect=ConnectionError):
            result = client.get_fund_industry_allocation("000001", "2025")
        assert result is None

    def test_fills_default_year_when_none(self, client):
        mock_resp = _mock_response(code=200, data=[])
        with patch("apis.market_client.requests.post", return_value=mock_resp) as mock_post:
            client.get_fund_industry_allocation("000001", None)

        call_args = mock_post.call_args[1]["json"]
        assert call_args["code"] == "000001"
        assert "year" in call_args
        # Default year should be current year (4 digits)
        assert len(call_args["year"]) == 4


# ---------------------------------------------------------------------------
# get_fund_stock_holds
# ---------------------------------------------------------------------------


class TestGetFundStockHolds:
    def test_returns_data_on_success(self, client):
        mock_resp = _mock_response(code=200, data=[
            {"sequence": 1, "stock_code": "600519", "stock_name": "贵州茅台",
             "pct": 8.52, "hold_shares": 120000, "hold_market_value": 210000000,
             "quarter": "2025Q1"},
        ])
        with patch("apis.market_client.requests.post", return_value=mock_resp) as mock_post:
            result = client.get_fund_stock_holds("000001", "2025")

        mock_post.assert_called_once_with(
            f"{client.base_url}/api/market/fund_public/portfolio_hold_stock",
            json={"code": "000001", "year": "2025"},
            timeout=5,
        )
        assert len(result) == 1
        assert result[0]["stock_code"] == "600519"

    def test_returns_none_when_code_not_200(self, client):
        mock_resp = _mock_response(code=404, data=None)
        with patch("apis.market_client.requests.post", return_value=mock_resp):
            result = client.get_fund_stock_holds("000001", "2025")
        assert result is None

    def test_returns_none_on_connection_error(self, client):
        with patch("apis.market_client.requests.post", side_effect=ConnectionError):
            result = client.get_fund_stock_holds("000001", "2025")
        assert result is None

    def test_fills_default_year_when_none(self, client):
        mock_resp = _mock_response(code=200, data=[])
        with patch("apis.market_client.requests.post", return_value=mock_resp) as mock_post:
            client.get_fund_stock_holds("000001", None)

        call_args = mock_post.call_args[1]["json"]
        assert call_args["code"] == "000001"
        assert "year" in call_args
        assert len(call_args["year"]) == 4


# ---------------------------------------------------------------------------
# get_fund_bond_holds
# ---------------------------------------------------------------------------


class TestGetFundBondHolds:
    def test_returns_data_on_success(self, client):
        mock_resp = _mock_response(code=200, data=[
            {"sequence": 1, "bond_code": "230016", "bond_name": "23附息国债16",
             "pct": 5.10, "hold_market_value": 85000000, "quarter": "2025Q1"},
        ])
        with patch("apis.market_client.requests.post", return_value=mock_resp) as mock_post:
            result = client.get_fund_bond_holds("000001", "2025")

        mock_post.assert_called_once_with(
            f"{client.base_url}/api/market/fund_public/portfolio_hold_bond",
            json={"code": "000001", "year": "2025"},
            timeout=5,
        )
        assert len(result) == 1
        assert result[0]["bond_code"] == "230016"

    def test_returns_none_when_code_not_200(self, client):
        mock_resp = _mock_response(code=404, data=None)
        with patch("apis.market_client.requests.post", return_value=mock_resp):
            result = client.get_fund_bond_holds("000001", "2025")
        assert result is None

    def test_returns_none_on_connection_error(self, client):
        with patch("apis.market_client.requests.post", side_effect=ConnectionError):
            result = client.get_fund_bond_holds("000001", "2025")
        assert result is None

    def test_fills_default_year_when_none(self, client):
        mock_resp = _mock_response(code=200, data=[])
        with patch("apis.market_client.requests.post", return_value=mock_resp) as mock_post:
            client.get_fund_bond_holds("000001", None)

        call_args = mock_post.call_args[1]["json"]
        assert call_args["code"] == "000001"
        assert "year" in call_args
        assert len(call_args["year"]) == 4


# ---------------------------------------------------------------------------
# _post error recovery
# ---------------------------------------------------------------------------


class TestPostErrorRecovery:
    def test_returns_none_on_timeout(self, client):
        import requests as requests_lib
        with patch("apis.market_client.requests.post",
                   side_effect=requests_lib.Timeout):
            result = client._post("/some/path", {"key": "val"})
        assert result is None

    def test_returns_none_on_invalid_json_response(self, client):
        bad_resp = MagicMock()
        bad_resp.json.side_effect = ValueError("not json")
        with patch("apis.market_client.requests.post", return_value=bad_resp):
            result = client._post("/some/path", {"key": "val"})
        assert result is None
