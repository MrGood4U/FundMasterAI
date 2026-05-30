import json
from unittest.mock import MagicMock, patch


class TestGetCurrentAllocation:
    def test_success(self, client):
        mock_service = MagicMock()
        mock_service.get_current_allocation.return_value = {
            "items": [
                {"asset_type": "stock", "market_value": 40000.00, "pct": 40.0, "total_cost": 35000.00},
                {"asset_type": "fund", "market_value": 30000.00, "pct": 30.0, "total_cost": 28000.00},
                {"asset_type": "bond", "market_value": 20000.00, "pct": 20.0, "total_cost": 20000.00},
                {"asset_type": "crypto", "market_value": 10000.00, "pct": 10.0, "total_cost": 12000.00},
            ],
            "total_market_value": 100000.00,
            "total_cost": 95000.00,
        }
        with patch("views.allocation_view.AllocationService", return_value=mock_service):
            resp = client.get("/api/portfolio/allocation/current")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert data["data"]["total_market_value"] == 100000.00
        assert len(data["data"]["items"]) == 4
        assert data["data"]["items"][0]["asset_type"] == "stock"
        assert data["data"]["items"][0]["pct"] == 40.0

    def test_empty_holdings(self, client):
        mock_service = MagicMock()
        mock_service.get_current_allocation.return_value = {
            "items": [
                {"asset_type": "bond", "market_value": 0.0, "pct": 0.0, "total_cost": 0.0},
                {"asset_type": "crypto", "market_value": 0.0, "pct": 0.0, "total_cost": 0.0},
                {"asset_type": "fund", "market_value": 0.0, "pct": 0.0, "total_cost": 0.0},
                {"asset_type": "stock", "market_value": 0.0, "pct": 0.0, "total_cost": 0.0},
            ],
            "total_market_value": 0.0,
            "total_cost": 0.0,
        }
        with patch("views.allocation_view.AllocationService", return_value=mock_service):
            resp = client.get("/api/portfolio/allocation/current")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert data["data"]["total_market_value"] == 0.0
        for item in data["data"]["items"]:
            assert item["pct"] == 0.0


class TestSetTargetAllocation:
    def test_success(self, client):
        mock_service = MagicMock()
        mock_service.set_target_allocation.return_value = {
            "targets": {"stock": 40, "fund": 30, "bond": 20, "crypto": 10},
            "message": "ok",
        }
        with patch("views.allocation_view.AllocationService", return_value=mock_service):
            resp = client.post("/api/portfolio/allocation/target", json={
                "stock": 40, "fund": 30, "bond": 20, "crypto": 10,
            })
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert data["data"]["message"] == "ok"

    def test_invalid_asset_type(self, client):
        mock_service = MagicMock()
        mock_service.set_target_allocation.return_value = {
            "error": "unknown asset_type: gold, must be one of ['stock', 'fund', 'bond', 'crypto']"
        }
        with patch("views.allocation_view.AllocationService", return_value=mock_service):
            resp = client.post("/api/portfolio/allocation/target", json={
                "stock": 40, "fund": 30, "gold": 30,
            })
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert data["code"] == 400
        assert "unknown asset_type" in data["message"]

    def test_sum_not_100(self, client):
        mock_service = MagicMock()
        mock_service.set_target_allocation.return_value = {
            "error": "target percentages sum to 80.0, must sum to 100"
        }
        with patch("views.allocation_view.AllocationService", return_value=mock_service):
            resp = client.post("/api/portfolio/allocation/target", json={
                "stock": 50, "fund": 30,
            })
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert data["code"] == 400
        assert "sum to 100" in data["message"]

    def test_empty_dict(self, client):
        mock_service = MagicMock()
        mock_service.set_target_allocation.return_value = {
            "error": "targets must be a non-empty dict"
        }
        with patch("views.allocation_view.AllocationService", return_value=mock_service):
            resp = client.post("/api/portfolio/allocation/target", json={})
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert data["code"] == 400


class TestGetTargetAllocation:
    def test_success(self, client):
        mock_service = MagicMock()
        mock_service.get_target_allocation.return_value = {
            "stock": 40.0, "fund": 30.0, "bond": 20.0, "crypto": 10.0,
        }
        with patch("views.allocation_view.AllocationService", return_value=mock_service):
            resp = client.get("/api/portfolio/allocation/target")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert data["data"]["stock"] == 40.0
        assert data["data"]["bond"] == 20.0

    def test_empty_targets(self, client):
        mock_service = MagicMock()
        mock_service.get_target_allocation.return_value = {}
        with patch("views.allocation_view.AllocationService", return_value=mock_service):
            resp = client.get("/api/portfolio/allocation/target")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert data["data"] == {}


class TestGetAllocationDrift:
    def test_success(self, client):
        mock_service = MagicMock()
        mock_service.get_drift.return_value = {
            "items": [
                {"asset_type": "stock", "current_pct": 45.0, "target_pct": 40.0,
                 "diff_pct": 5.0, "status": "正常"},
                {"asset_type": "fund", "current_pct": 25.0, "target_pct": 30.0,
                 "diff_pct": -5.0, "status": "正常"},
                {"asset_type": "bond", "current_pct": 10.0, "target_pct": 20.0,
                 "diff_pct": -10.0, "status": "低配"},
                {"asset_type": "crypto", "current_pct": 20.0, "target_pct": 10.0,
                 "diff_pct": 10.0, "status": "超配"},
            ],
            "total_market_value": 100000.00,
        }
        with patch("views.allocation_view.AllocationService", return_value=mock_service):
            resp = client.get("/api/portfolio/allocation/drift")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert len(data["data"]["items"]) == 4
        # 超配
        assert data["data"]["items"][3]["status"] == "超配"
        assert data["data"]["items"][3]["diff_pct"] == 10.0
        # 低配
        assert data["data"]["items"][2]["status"] == "低配"
        assert data["data"]["items"][2]["diff_pct"] == -10.0

    def test_all_normal(self, client):
        mock_service = MagicMock()
        mock_service.get_drift.return_value = {
            "items": [
                {"asset_type": "stock", "current_pct": 41.0, "target_pct": 40.0,
                 "diff_pct": 1.0, "status": "正常"},
            ],
            "total_market_value": 50000.00,
        }
        with patch("views.allocation_view.AllocationService", return_value=mock_service):
            resp = client.get("/api/portfolio/allocation/drift")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert all(item["status"] == "正常" for item in data["data"]["items"])
