import json
from unittest.mock import MagicMock, patch


class TestGetBooks:
    def test_returns_success(self, client):
        mock_service = MagicMock()
        mock_service.get_books.return_value = {
            "bids": [[96500.5, 0.5]], "asks": [[96550.0, 0.8]]
        }
        with patch("views.crypto_view.CryptoService", return_value=mock_service):
            resp = client.post("/api/market/crypto/books",
                               json={"symbol": "BTC"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert len(data["data"]["bids"]) == 1

    def test_missing_json_body(self, client):
        resp = client.post("/api/market/crypto/books", data=None)
        assert resp.status_code == 404
        data = json.loads(resp.data)
        assert data["message"] == "args not found"

    def test_missing_symbol(self, client):
        resp = client.post("/api/market/crypto/books", json={})
        assert resp.status_code == 404
        data = json.loads(resp.data)
        assert data["message"] == "symbol is required"


class TestGetTicker:
    def test_returns_success(self, client):
        mock_service = MagicMock()
        mock_service.get_ticker.return_value = {
            "symbol": "BTC-USDT", "last_price": 96520.5
        }
        with patch("views.crypto_view.CryptoService", return_value=mock_service):
            resp = client.post("/api/market/crypto/ticker",
                               json={"symbol": "BTC"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert data["data"]["last_price"] == 96520.5

    def test_missing_json_body(self, client):
        resp = client.post("/api/market/crypto/ticker", data=None)
        assert resp.status_code == 404

    def test_missing_symbol(self, client):
        resp = client.post("/api/market/crypto/ticker", json={})
        assert resp.status_code == 404


class TestGetKlines:
    def test_returns_success(self, client):
        mock_service = MagicMock()
        mock_service.get_klines.return_value = [
            {"start_time": 1716854400000, "close_price": 96550.0}
        ]
        with patch("views.crypto_view.CryptoService", return_value=mock_service):
            resp = client.post("/api/market/crypto/klines",
                               json={"symbol": "BTC", "start_time": 1716854400,
                                     "end_time": 1716854460})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert len(data["data"]) == 1

    def test_default_params(self, client):
        mock_service = MagicMock()
        mock_service.get_klines.return_value = []
        with patch("views.crypto_view.CryptoService", return_value=mock_service):
            resp = client.post("/api/market/crypto/klines",
                               json={"symbol": "ETH", "start_time": 0, "end_time": 1})
        args, kwargs = mock_service.get_klines.call_args
        assert kwargs["market_type"] == "SPOT"
        assert kwargs["interval"] == "1m"
        assert kwargs["limit"] == 1000

    def test_missing_start_time(self, client):
        resp = client.post("/api/market/crypto/klines",
                           json={"symbol": "BTC", "end_time": 1716854460})
        assert resp.status_code == 404

    def test_missing_end_time(self, client):
        resp = client.post("/api/market/crypto/klines",
                           json={"symbol": "BTC", "start_time": 1716854400})
        assert resp.status_code == 404


class TestGetMa:
    def test_returns_success(self, client):
        mock_service = MagicMock()
        mock_service.get_ma.return_value = {
            "symbol": "BTC-USDT", "interval": "1m", "ma_periods": [5],
            "items": [{"datetime": 1716854400000, "close_price": 96550.0, "ma": [None]}]
        }
        with patch("views.crypto_view.CryptoService", return_value=mock_service):
            resp = client.post("/api/market/crypto/ma",
                               json={"symbol": "BTC"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200

    def test_default_params_passed(self, client):
        mock_service = MagicMock()
        mock_service.get_ma.return_value = {}
        with patch("views.crypto_view.CryptoService", return_value=mock_service):
            resp = client.post("/api/market/crypto/ma",
                               json={"symbol": "ETH"})
        _, kwargs = mock_service.get_ma.call_args
        assert kwargs["market_type"] == "SPOT"
        assert kwargs["interval"] == "1m"
        assert kwargs["start_time"] == 0
        assert kwargs["end_time"] == 0
        assert kwargs["limit"] == 500

    def test_missing_json_body(self, client):
        resp = client.post("/api/market/crypto/ma", data=None)
        assert resp.status_code == 404

    def test_missing_symbol(self, client):
        resp = client.post("/api/market/crypto/ma", json={})
        assert resp.status_code == 404


class TestRootEndpoint:
    def test_hello_world(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "message" in data
