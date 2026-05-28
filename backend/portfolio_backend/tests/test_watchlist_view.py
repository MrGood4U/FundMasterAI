import json
from unittest.mock import MagicMock, patch


class TestAddToWatchlist:
    def test_success(self, client):
        mock_service = MagicMock()
        mock_service.add.return_value = {"id": 1}
        with patch("views.watchlist_view.WatchlistService", return_value=mock_service):
            resp = client.post("/api/portfolio/watchlist/create", json={
                "asset_type": "stock",
                "asset_code": "000001",
                "asset_name": "平安银行",
                "target_price": 10.00,
                "priority": 3,
                "notes": "watching",
            })
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert data["data"]["id"] == 1

    def test_missing_required_fields(self, client):
        mock_service = MagicMock()
        mock_service.add.return_value = {"error": "asset_type is required"}
        with patch("views.watchlist_view.WatchlistService", return_value=mock_service):
            resp = client.post("/api/portfolio/watchlist/create", json={})
        assert resp.status_code == 400


class TestRemoveFromWatchlist:
    def test_success(self, client):
        mock_service = MagicMock()
        mock_service.remove.return_value = True
        with patch("views.watchlist_view.WatchlistService", return_value=mock_service):
            resp = client.post("/api/portfolio/watchlist/delete", json={
                "watchlist_id": 1,
            })
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200

    def test_missing_watchlist_id(self, client):
        resp = client.post("/api/portfolio/watchlist/delete", json={})
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert data["message"] == "watchlist_id is required"

    def test_not_found(self, client):
        mock_service = MagicMock()
        mock_service.remove.return_value = False
        with patch("views.watchlist_view.WatchlistService", return_value=mock_service):
            resp = client.post("/api/portfolio/watchlist/delete", json={
                "watchlist_id": 999,
            })
        assert resp.status_code == 404


class TestListWatchlist:
    def test_success_defaults(self, client):
        mock_service = MagicMock()
        mock_service.list_by_user.return_value = {
            "items": [{"id": 1, "asset_type": "stock", "asset_code": "000001"}],
            "total": 1, "page": 1, "page_size": 20,
        }
        with patch("views.watchlist_view.WatchlistService", return_value=mock_service):
            resp = client.get("/api/portfolio/watchlist/list")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert data["data"]["total"] == 1

    def test_with_asset_type_filter(self, client):
        mock_service = MagicMock()
        mock_service.list_by_user.return_value = {
            "items": [], "total": 0, "page": 1, "page_size": 20,
        }
        with patch("views.watchlist_view.WatchlistService", return_value=mock_service):
            resp = client.get("/api/portfolio/watchlist/list?"
                              "asset_type=crypto&page=2&page_size=5")
        assert resp.status_code == 200
        mock_service.list_by_user.assert_called_once_with(
            asset_type="crypto", page=2, page_size=5,
        )

    def test_empty_result(self, client):
        mock_service = MagicMock()
        mock_service.list_by_user.return_value = {
            "items": [], "total": 0, "page": 1, "page_size": 20,
        }
        with patch("views.watchlist_view.WatchlistService", return_value=mock_service):
            resp = client.get("/api/portfolio/watchlist/list")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["data"]["items"] == []
