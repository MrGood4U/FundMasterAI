import json
from unittest.mock import MagicMock, patch


class TestGetOneSpot:
    def test_returns_success(self, client):
        mock_service = MagicMock()
        mock_service.get_a_spot.return_value = [{"stock_code": "000001", "latest_price": 12.50}]
        with patch("views.stock_view.StockService", return_value=mock_service):
            resp = client.post("/api/market/stock/a/one_spot",
                               json={"platform": "eastmoney", "code": "000001"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert len(data["data"]) == 1

    def test_missing_json_body(self, client):
        resp = client.post("/api/market/stock/a/one_spot",
                           data=None,
                           content_type="application/json")
        assert resp.status_code in (400, 415)  # flask-openapi3 varies by version

    def test_missing_platform(self, client):
        resp = client.post("/api/market/stock/a/one_spot", json={"code": "000001"})
        assert resp.status_code == 404
        data = json.loads(resp.data)
        assert data["message"] == "args not found"


class TestGetAllASpot:
    def test_returns_success(self, client):
        mock_service = MagicMock()
        mock_service.get_all_a_spot.return_value = [
            {"stock_code": "000001"}, {"stock_code": "000002"}
        ]
        with patch("views.stock_view.StockService", return_value=mock_service):
            resp = client.post("/api/market/stock/a/all_spot",
                               json={"platform": "eastmoney"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert len(data["data"]) == 2

    def test_missing_platform(self, client):
        resp = client.post("/api/market/stock/a/all_spot", json={})
        assert resp.status_code == 404


class TestGetAHist:
    def test_returns_success(self, client):
        mock_service = MagicMock()
        mock_service.get_a_hist.return_value = [{"date": "2026-05-20", "close": 12.50}]
        with patch("views.stock_view.StockService", return_value=mock_service):
            resp = client.post("/api/market/stock/a/hist",
                               json={"platform": "eastmoney", "code": "000001",
                                     "period": "daily", "start_date": "2026-05-01",
                                     "end_date": "2026-05-28", "adjust": "qfq"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200

    def test_missing_code(self, client):
        resp = client.post("/api/market/stock/a/hist",
                           json={"platform": "eastmoney"})
        assert resp.status_code == 404

    def test_missing_platform(self, client):
        resp = client.post("/api/market/stock/a/hist",
                           json={"code": "000001"})
        assert resp.status_code == 404


class TestGetABidAsk:
    def test_returns_success(self, client):
        mock_service = MagicMock()
        mock_service.get_a_bid_ask.return_value = [{"latest_price": 12.50}]
        with patch("views.stock_view.StockService", return_value=mock_service):
            resp = client.post("/api/market/stock/a/bid_ask",
                               json={"code": "000001", "platform": "eastmoney"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200

    def test_missing_code(self, client):
        resp = client.post("/api/market/stock/a/bid_ask",
                           json={"platform": "eastmoney"})
        assert resp.status_code == 404
