import json
from unittest.mock import MagicMock, patch


class TestListHoldings:
    def test_success_defaults(self, client):
        mock_service = MagicMock()
        mock_service.get_holdings.return_value = {
            "items": [
                {
                    "asset_type": "stock", "asset_code": "000001",
                    "asset_name": "平安银行", "total_quantity": 100,
                    "avg_cost": 12.50, "total_cost": 1250.00,
                    "current_price": 13.00, "market_value": 1300.00,
                    "unrealized_pnl": 50.00, "unrealized_pnl_pct": 4.0,
                    "portfolio_tags": ["长线"],
                }
            ],
            "total": 1, "page": 1, "page_size": 20,
        }
        with patch("views.holding_view.HoldingService", return_value=mock_service):
            resp = client.get("/api/portfolio/holding/list")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert data["data"]["total"] == 1
        assert len(data["data"]["items"]) == 1
        assert data["data"]["items"][0]["asset_code"] == "000001"

    def test_with_asset_type_filter(self, client):
        mock_service = MagicMock()
        mock_service.get_holdings.return_value = {
            "items": [], "total": 0, "page": 1, "page_size": 20,
        }
        with patch("views.holding_view.HoldingService", return_value=mock_service):
            resp = client.get("/api/portfolio/holding/list?asset_type=fund&page=1&page_size=10")
        assert resp.status_code == 200
        mock_service.get_holdings.assert_called_once_with(
            asset_type="fund", page=1, page_size=10,
        )

    def test_with_pagination(self, client):
        mock_service = MagicMock()
        mock_service.get_holdings.return_value = {
            "items": [], "total": 0, "page": 3, "page_size": 5,
        }
        with patch("views.holding_view.HoldingService", return_value=mock_service):
            resp = client.get("/api/portfolio/holding/list?page=3&page_size=5")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["data"]["page"] == 3
        assert data["data"]["page_size"] == 5


class TestGetHoldingDetail:
    def test_success(self, client):
        mock_service = MagicMock()
        mock_service.get_holding_detail.return_value = {
            "asset_type": "stock", "asset_code": "000001",
            "asset_name": "平安银行", "total_quantity": 100,
            "avg_cost": 12.50, "total_cost": 1250.00,
            "current_price": 13.00, "market_value": 1300.00,
            "unrealized_pnl": 50.00, "unrealized_pnl_pct": 4.0,
            "transactions": [
                {"id": 1, "trans_type": "buy", "price": 12.50, "quantity": 100},
            ],
        }
        with patch("views.holding_view.HoldingService", return_value=mock_service):
            resp = client.get("/api/portfolio/holding/detail?"
                              "asset_type=stock&asset_code=000001")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert len(data["data"]["transactions"]) == 1

    def test_missing_asset_type(self, client):
        resp = client.get("/api/portfolio/holding/detail?asset_code=000001")
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert data["message"] == "asset_type and asset_code are required"

    def test_missing_asset_code(self, client):
        resp = client.get("/api/portfolio/holding/detail?asset_type=stock")
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert data["message"] == "asset_type and asset_code are required"

    def test_not_found(self, client):
        mock_service = MagicMock()
        mock_service.get_holding_detail.return_value = None
        with patch("views.holding_view.HoldingService", return_value=mock_service):
            resp = client.get("/api/portfolio/holding/detail?"
                              "asset_type=stock&asset_code=999999")
        assert resp.status_code == 404
