import json
from unittest.mock import MagicMock, patch


class TestGetDetailHold:
    def test_success(self, client):
        mock_service = MagicMock()
        mock_service.get_detail_hold.return_value = [
            {"asset_type": "股票", "pct": 72.35},
            {"asset_type": "债券", "pct": 18.20},
            {"asset_type": "现金", "pct": 9.45},
        ]

        with patch("views.fund_detail_view.FundDetailService", return_value=mock_service):
            resp = client.post("/api/portfolio/fund/detail_hold",
                               json={"code": "000001", "date": "20241231"})

        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert len(data["data"]) == 3
        assert data["data"][0]["asset_type"] == "股票"

    def test_success_default_date(self, client):
        mock_service = MagicMock()
        mock_service.get_detail_hold.return_value = [
            {"asset_type": "股票", "pct": 65.00},
        ]

        with patch("views.fund_detail_view.FundDetailService", return_value=mock_service):
            resp = client.post("/api/portfolio/fund/detail_hold",
                               json={"code": "000001"})

        assert resp.status_code == 200
        mock_service.get_detail_hold.assert_called_once_with(code="000001", date=None)

    def test_missing_code(self, client):
        resp = client.post("/api/portfolio/fund/detail_hold",
                           json={"date": "20241231"})
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert data["message"] == "code is required"

    def test_not_found(self, client):
        mock_service = MagicMock()
        mock_service.get_detail_hold.return_value = None

        with patch("views.fund_detail_view.FundDetailService", return_value=mock_service):
            resp = client.post("/api/portfolio/fund/detail_hold",
                               json={"code": "999999"})

        assert resp.status_code == 404
        data = json.loads(resp.data)
        assert data["code"] == 404


class TestGetIndustryAllocation:
    def test_success(self, client):
        mock_service = MagicMock()
        mock_service.get_industry_allocation.return_value = [
            {"sequence": 1, "industry_category": "制造业", "pct": 35.42,
             "market_value": 1250000000, "as_of_date": "2025-03-31"},
            {"sequence": 2, "industry_category": "金融业", "pct": 18.10,
             "market_value": 650000000, "as_of_date": "2025-03-31"},
        ]

        with patch("views.fund_detail_view.FundDetailService", return_value=mock_service):
            resp = client.post("/api/portfolio/fund/industry_allocation",
                               json={"code": "000001", "year": "2025"})

        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert len(data["data"]) == 2
        assert data["data"][0]["industry_category"] == "制造业"

    def test_success_default_year(self, client):
        mock_service = MagicMock()
        mock_service.get_industry_allocation.return_value = []

        with patch("views.fund_detail_view.FundDetailService", return_value=mock_service):
            resp = client.post("/api/portfolio/fund/industry_allocation",
                               json={"code": "000001"})

        assert resp.status_code == 200
        mock_service.get_industry_allocation.assert_called_once_with(code="000001", year=None)

    def test_missing_code(self, client):
        resp = client.post("/api/portfolio/fund/industry_allocation",
                           json={"year": "2025"})
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert data["message"] == "code is required"

    def test_not_found(self, client):
        mock_service = MagicMock()
        mock_service.get_industry_allocation.return_value = None

        with patch("views.fund_detail_view.FundDetailService", return_value=mock_service):
            resp = client.post("/api/portfolio/fund/industry_allocation",
                               json={"code": "999999"})

        assert resp.status_code == 404
        data = json.loads(resp.data)
        assert data["code"] == 404


class TestGetStockHolds:
    def test_success(self, client):
        mock_service = MagicMock()
        mock_service.get_stock_holds.return_value = [
            {"sequence": 1, "stock_code": "600519", "stock_name": "贵州茅台",
             "pct": 8.52, "hold_shares": 120000, "hold_market_value": 210000000,
             "quarter": "2025Q1"},
            {"sequence": 2, "stock_code": "000858", "stock_name": "五粮液",
             "pct": 5.10, "hold_shares": 200000, "hold_market_value": 125000000,
             "quarter": "2025Q1"},
        ]

        with patch("views.fund_detail_view.FundDetailService", return_value=mock_service):
            resp = client.post("/api/portfolio/fund/stock_holds",
                               json={"code": "000001", "year": "2025"})

        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert len(data["data"]) == 2
        assert data["data"][0]["stock_code"] == "600519"

    def test_success_default_year(self, client):
        mock_service = MagicMock()
        mock_service.get_stock_holds.return_value = []

        with patch("views.fund_detail_view.FundDetailService", return_value=mock_service):
            resp = client.post("/api/portfolio/fund/stock_holds",
                               json={"code": "000001"})

        assert resp.status_code == 200
        mock_service.get_stock_holds.assert_called_once_with(code="000001", year=None)

    def test_missing_code(self, client):
        resp = client.post("/api/portfolio/fund/stock_holds",
                           json={"year": "2025"})
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert data["message"] == "code is required"

    def test_not_found(self, client):
        mock_service = MagicMock()
        mock_service.get_stock_holds.return_value = None

        with patch("views.fund_detail_view.FundDetailService", return_value=mock_service):
            resp = client.post("/api/portfolio/fund/stock_holds",
                               json={"code": "999999"})

        assert resp.status_code == 404
        data = json.loads(resp.data)
        assert data["code"] == 404


class TestGetBondHolds:
    def test_success(self, client):
        mock_service = MagicMock()
        mock_service.get_bond_holds.return_value = [
            {"sequence": 1, "bond_code": "230016", "bond_name": "23附息国债16",
             "pct": 5.10, "hold_market_value": 85000000, "quarter": "2025Q1"},
            {"sequence": 2, "bond_code": "210218", "bond_name": "21国开18",
             "pct": 3.20, "hold_market_value": 52000000, "quarter": "2025Q1"},
        ]

        with patch("views.fund_detail_view.FundDetailService", return_value=mock_service):
            resp = client.post("/api/portfolio/fund/bond_holds",
                               json={"code": "000001", "year": "2025"})

        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert len(data["data"]) == 2
        assert data["data"][0]["bond_code"] == "230016"

    def test_success_default_year(self, client):
        mock_service = MagicMock()
        mock_service.get_bond_holds.return_value = []

        with patch("views.fund_detail_view.FundDetailService", return_value=mock_service):
            resp = client.post("/api/portfolio/fund/bond_holds",
                               json={"code": "000001"})

        assert resp.status_code == 200
        mock_service.get_bond_holds.assert_called_once_with(code="000001", year=None)

    def test_missing_code(self, client):
        resp = client.post("/api/portfolio/fund/bond_holds",
                           json={"year": "2025"})
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert data["message"] == "code is required"

    def test_not_found(self, client):
        mock_service = MagicMock()
        mock_service.get_bond_holds.return_value = None

        with patch("views.fund_detail_view.FundDetailService", return_value=mock_service):
            resp = client.post("/api/portfolio/fund/bond_holds",
                               json={"code": "999999"})

        assert resp.status_code == 404
        data = json.loads(resp.data)
        assert data["code"] == 404
