import json
from unittest.mock import MagicMock, patch


class TestCreateAlert:
    def test_success_price_mode(self, client):
        mock_service = MagicMock()
        mock_service.create.return_value = {"id": 1}
        with patch("views.alert_view.AlertService", return_value=mock_service):
            resp = client.post("/api/portfolio/alert/create", json={
                "asset_type": "stock",
                "asset_code": "000001",
                "alert_type": "price_above",
                "trigger_mode": "price",
                "trigger_price": 15.00,
                "notes": "test alert",
            })
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert data["data"]["id"] == 1

    def test_success_pct_mode(self, client):
        mock_service = MagicMock()
        mock_service.create.return_value = {"id": 2}
        with patch("views.alert_view.AlertService", return_value=mock_service):
            resp = client.post("/api/portfolio/alert/create", json={
                "asset_type": "fund",
                "asset_code": "510050",
                "alert_type": "stop_profit",
                "trigger_mode": "pct",
                "trigger_pct": 0.15,
            })
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200

    def test_service_returns_error(self, client):
        mock_service = MagicMock()
        mock_service.create.return_value = {"error": "trigger_price is required when trigger_mode is price"}
        with patch("views.alert_view.AlertService", return_value=mock_service):
            resp = client.post("/api/portfolio/alert/create", json={
                "asset_type": "stock",
                "asset_code": "000001",
                "alert_type": "price_above",
                "trigger_mode": "price",
            })
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert data["code"] == 400


class TestGetAlert:
    def test_success(self, client):
        mock_service = MagicMock()
        mock_service.get_by_id.return_value = {
            "id": 1, "asset_type": "stock", "asset_code": "000001",
            "alert_type": "price_above", "trigger_mode": "price",
            "trigger_price": 15.00, "is_enabled": 1,
        }
        with patch("views.alert_view.AlertService", return_value=mock_service):
            resp = client.get("/api/portfolio/alert/1")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert data["data"]["id"] == 1

    def test_not_found(self, client):
        mock_service = MagicMock()
        mock_service.get_by_id.return_value = {}
        with patch("views.alert_view.AlertService", return_value=mock_service):
            resp = client.get("/api/portfolio/alert/999")
        assert resp.status_code == 404


class TestUpdateAlert:
    def test_success(self, client):
        mock_service = MagicMock()
        mock_service.update.return_value = True
        with patch("views.alert_view.AlertService", return_value=mock_service):
            resp = client.post("/api/portfolio/alert/update", json={
                "alert_id": 1,
                "trigger_price": 16.00,
                "is_enabled": 0,
                "notes": "updated",
            })
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200

    def test_missing_alert_id(self, client):
        resp = client.post("/api/portfolio/alert/update", json={
            "trigger_price": 16.00,
        })
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert data["message"] == "alert_id is required"

    def test_not_found(self, client):
        mock_service = MagicMock()
        mock_service.update.return_value = False
        with patch("views.alert_view.AlertService", return_value=mock_service):
            resp = client.post("/api/portfolio/alert/update", json={
                "alert_id": 999,
                "trigger_price": 16.00,
            })
        assert resp.status_code == 404


class TestDeleteAlert:
    def test_success(self, client):
        mock_service = MagicMock()
        mock_service.delete.return_value = True
        with patch("views.alert_view.AlertService", return_value=mock_service):
            resp = client.post("/api/portfolio/alert/delete", json={
                "alert_id": 1,
            })
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200

    def test_missing_alert_id(self, client):
        resp = client.post("/api/portfolio/alert/delete", json={})
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert data["message"] == "alert_id is required"

    def test_not_found(self, client):
        mock_service = MagicMock()
        mock_service.delete.return_value = False
        with patch("views.alert_view.AlertService", return_value=mock_service):
            resp = client.post("/api/portfolio/alert/delete", json={
                "alert_id": 999,
            })
        assert resp.status_code == 404


class TestListAlerts:
    def test_success_defaults(self, client):
        mock_service = MagicMock()
        mock_service.list_by_user.return_value = {
            "items": [{"id": 1, "alert_type": "price_above"}],
            "total": 1, "page": 1, "page_size": 20,
        }
        with patch("views.alert_view.AlertService", return_value=mock_service):
            resp = client.get("/api/portfolio/alert/list")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert data["data"]["total"] == 1

    def test_with_filter_is_enabled_true(self, client):
        mock_service = MagicMock()
        mock_service.list_by_user.return_value = {
            "items": [], "total": 0, "page": 1, "page_size": 20,
        }
        with patch("views.alert_view.AlertService", return_value=mock_service):
            resp = client.get("/api/portfolio/alert/list?is_enabled=1")
        assert resp.status_code == 200
        # Verify service was called with is_enabled=True
        mock_service.list_by_user.assert_called_once_with(
            is_enabled=True, asset_type=None, page=1, page_size=20,
        )

    def test_with_filter_is_enabled_false(self, client):
        mock_service = MagicMock()
        mock_service.list_by_user.return_value = {
            "items": [], "total": 0, "page": 1, "page_size": 20,
        }
        with patch("views.alert_view.AlertService", return_value=mock_service):
            resp = client.get("/api/portfolio/alert/list?is_enabled=0")
        assert resp.status_code == 200
        mock_service.list_by_user.assert_called_once_with(
            is_enabled=False, asset_type=None, page=1, page_size=20,
        )

    def test_with_asset_type_filter(self, client):
        mock_service = MagicMock()
        mock_service.list_by_user.return_value = {
            "items": [], "total": 0, "page": 1, "page_size": 20,
        }
        with patch("views.alert_view.AlertService", return_value=mock_service):
            resp = client.get("/api/portfolio/alert/list?asset_type=crypto&page=1&page_size=10")
        assert resp.status_code == 200
        mock_service.list_by_user.assert_called_once_with(
            is_enabled=None, asset_type="crypto", page=1, page_size=10,
        )
