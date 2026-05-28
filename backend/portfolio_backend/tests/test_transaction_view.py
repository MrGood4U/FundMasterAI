import json
from unittest.mock import MagicMock, patch


class TestCreateTransaction:
    def test_success(self, client):
        mock_service = MagicMock()
        mock_service.create.return_value = {"id": 1}
        with patch("views.transaction_view.TransactionService", return_value=mock_service):
            resp = client.post("/api/portfolio/transaction/create", json={
                "asset_type": "stock",
                "asset_code": "000001",
                "asset_name": "平安银行",
                "trans_type": "buy",
                "price": 12.50,
                "quantity": 100,
                "fee": 5.0,
                "trans_date": "2026-05-20",
                "portfolio_tag": "长线",
                "notes": "test",
            })
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert data["data"]["id"] == 1

    def test_missing_required_fields(self, client):
        mock_service = MagicMock()
        mock_service.create.return_value = {"error": "asset_type is required"}
        with patch("views.transaction_view.TransactionService", return_value=mock_service):
            resp = client.post("/api/portfolio/transaction/create", json={})
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert data["code"] == 400

    def test_invalid_trans_type(self, client):
        mock_service = MagicMock()
        mock_service.create.return_value = {"error": "trans_type must be buy or sell"}
        with patch("views.transaction_view.TransactionService", return_value=mock_service):
            resp = client.post("/api/portfolio/transaction/create", json={
                "asset_type": "stock",
                "asset_code": "000001",
                "trans_type": "invalid",
                "price": 12.50,
                "quantity": 100,
                "trans_date": "2026-05-20",
            })
        assert resp.status_code == 400


class TestGetTransaction:
    def test_success(self, client):
        mock_service = MagicMock()
        mock_service.get_by_id.return_value = {
            "id": 1, "asset_type": "stock", "asset_code": "000001",
            "asset_name": "平安银行", "trans_type": "buy", "price": 12.50,
            "quantity": 100, "fee": 5.0, "trans_date": "2026-05-20",
        }
        with patch("views.transaction_view.TransactionService", return_value=mock_service):
            resp = client.get("/api/portfolio/transaction/1")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert data["data"]["id"] == 1

    def test_not_found(self, client):
        mock_service = MagicMock()
        mock_service.get_by_id.return_value = {}
        with patch("views.transaction_view.TransactionService", return_value=mock_service):
            resp = client.get("/api/portfolio/transaction/999")
        assert resp.status_code == 404


class TestUpdateTransaction:
    def test_success(self, client):
        mock_service = MagicMock()
        mock_service.update.return_value = True
        with patch("views.transaction_view.TransactionService", return_value=mock_service):
            resp = client.post("/api/portfolio/transaction/update", json={
                "trans_id": 1,
                "price": 13.00,
                "quantity": 200,
                "notes": "updated",
            })
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200

    def test_missing_trans_id(self, client):
        resp = client.post("/api/portfolio/transaction/update", json={
            "price": 13.00,
        })
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert data["message"] == "trans_id is required"

    def test_not_found(self, client):
        mock_service = MagicMock()
        mock_service.update.return_value = False
        with patch("views.transaction_view.TransactionService", return_value=mock_service):
            resp = client.post("/api/portfolio/transaction/update", json={
                "trans_id": 999,
                "price": 13.00,
            })
        assert resp.status_code == 404


class TestDeleteTransaction:
    def test_success(self, client):
        mock_service = MagicMock()
        mock_service.delete.return_value = True
        with patch("views.transaction_view.TransactionService", return_value=mock_service):
            resp = client.post("/api/portfolio/transaction/delete", json={
                "trans_id": 1,
            })
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200

    def test_missing_trans_id(self, client):
        resp = client.post("/api/portfolio/transaction/delete", json={})
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert data["message"] == "trans_id is required"

    def test_not_found(self, client):
        mock_service = MagicMock()
        mock_service.delete.return_value = False
        with patch("views.transaction_view.TransactionService", return_value=mock_service):
            resp = client.post("/api/portfolio/transaction/delete", json={
                "trans_id": 999,
            })
        assert resp.status_code == 404


class TestListTransactions:
    def test_success_with_default_pagination(self, client):
        mock_service = MagicMock()
        mock_service.list_by_user.return_value = {
            "items": [{"id": 1, "asset_type": "stock", "asset_code": "000001"}],
            "total": 1, "page": 1, "page_size": 20,
        }
        with patch("views.transaction_view.TransactionService", return_value=mock_service):
            resp = client.get("/api/portfolio/transaction/list")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert data["data"]["total"] == 1
        assert data["data"]["page"] == 1
        assert data["data"]["page_size"] == 20
        assert len(data["data"]["items"]) == 1

    def test_with_filters_and_pagination(self, client):
        mock_service = MagicMock()
        mock_service.list_by_user.return_value = {
            "items": [],
            "total": 0, "page": 2, "page_size": 10,
        }
        with patch("views.transaction_view.TransactionService", return_value=mock_service):
            resp = client.get("/api/portfolio/transaction/list?"
                              "asset_type=stock&trans_type=buy&"
                              "start_date=2026-01-01&end_date=2026-05-29&"
                              "page=2&page_size=10")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["data"]["page"] == 2
        assert data["data"]["page_size"] == 10

    def test_empty_result(self, client):
        mock_service = MagicMock()
        mock_service.list_by_user.return_value = {
            "items": [], "total": 0, "page": 1, "page_size": 20,
        }
        with patch("views.transaction_view.TransactionService", return_value=mock_service):
            resp = client.get("/api/portfolio/transaction/list")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["data"]["total"] == 0
        assert data["data"]["items"] == []
