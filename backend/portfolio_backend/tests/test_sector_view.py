import json
from unittest.mock import MagicMock, patch


class TestGetSectorExposure:
    def test_success(self, client):
        mock_service = MagicMock()
        mock_service.get_sector_exposure.return_value = {
            "items": [
                {"sector": "科技", "market_value": 35000.00, "pct": 35.0},
                {"sector": "金融", "market_value": 25000.00, "pct": 25.0},
                {"sector": "消费", "market_value": 20000.00, "pct": 20.0},
                {"sector": "医药", "market_value": 10000.00, "pct": 10.0},
                {"sector": "其他", "market_value": 10000.00, "pct": 10.0},
            ],
            "total_market_value": 100000.00,
        }
        with patch("views.sector_view.SectorService", return_value=mock_service):
            resp = client.get("/api/portfolio/sector/exposure")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert data["data"]["total_market_value"] == 100000.00
        assert len(data["data"]["items"]) == 5
        assert data["data"]["items"][0]["sector"] == "科技"
        assert data["data"]["items"][0]["pct"] == 35.0

    def test_empty_holdings(self, client):
        mock_service = MagicMock()
        mock_service.get_sector_exposure.return_value = {
            "items": [],
            "total_market_value": 0.0,
        }
        with patch("views.sector_view.SectorService", return_value=mock_service):
            resp = client.get("/api/portfolio/sector/exposure")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert data["data"]["items"] == []
        assert data["data"]["total_market_value"] == 0.0

    def test_bond_and_crypto_sectors(self, client):
        """债券归入"债券"行业，加密货币归入"加密货币"行业。"""
        mock_service = MagicMock()
        mock_service.get_sector_exposure.return_value = {
            "items": [
                {"sector": "债券", "market_value": 50000.00, "pct": 50.0},
                {"sector": "加密货币", "market_value": 30000.00, "pct": 30.0},
                {"sector": "金融", "market_value": 20000.00, "pct": 20.0},
            ],
            "total_market_value": 100000.00,
        }
        with patch("views.sector_view.SectorService", return_value=mock_service):
            resp = client.get("/api/portfolio/sector/exposure")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        sectors = {item["sector"]: item["pct"] for item in data["data"]["items"]}
        assert sectors["债券"] == 50.0
        assert sectors["加密货币"] == 30.0


class TestGetSectorConcentration:
    def test_success(self, client):
        mock_service = MagicMock()
        mock_service.get_sector_concentration.return_value = {
            "top3_sectors": [
                {"sector": "科技", "market_value": 35000.00, "pct": 35.0},
                {"sector": "金融", "market_value": 25000.00, "pct": 25.0},
                {"sector": "消费", "market_value": 20000.00, "pct": 20.0},
            ],
            "top3_sectors_pct": 80.0,
            "top5_stocks": [
                {"code": "300750", "name": "宁德时代", "market_value": 15000.00, "pct": 15.0},
                {"code": "600519", "name": "贵州茅台", "market_value": 12000.00, "pct": 12.0},
            ],
            "top5_stocks_pct": 27.0,
            "warnings": [
                "前3大行业占比 80.0%，集中度过高",
            ],
        }
        with patch("views.sector_view.SectorService", return_value=mock_service):
            resp = client.get("/api/portfolio/sector/concentration")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert data["data"]["top3_sectors_pct"] == 80.0
        assert data["data"]["top5_stocks_pct"] == 27.0
        assert len(data["data"]["warnings"]) == 1

    def test_no_warnings(self, client):
        mock_service = MagicMock()
        mock_service.get_sector_concentration.return_value = {
            "top3_sectors": [
                {"sector": "金融", "market_value": 15000.00, "pct": 15.0},
            ],
            "top3_sectors_pct": 15.0,
            "top5_stocks": [
                {"code": "000001", "name": "平安银行", "market_value": 5000.00, "pct": 5.0},
            ],
            "top5_stocks_pct": 5.0,
            "warnings": [],
        }
        with patch("views.sector_view.SectorService", return_value=mock_service):
            resp = client.get("/api/portfolio/sector/concentration")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert data["data"]["warnings"] == []

    def test_single_stock_high_concentration(self, client):
        """单一个股占比超过20%触发警告。"""
        mock_service = MagicMock()
        mock_service.get_sector_concentration.return_value = {
            "top3_sectors": [
                {"sector": "科技", "market_value": 30000.00, "pct": 30.0},
            ],
            "top3_sectors_pct": 30.0,
            "top5_stocks": [
                {"code": "300750", "name": "宁德时代", "market_value": 25000.00, "pct": 25.0},
            ],
            "top5_stocks_pct": 25.0,
            "warnings": ["宁德时代(300750) 单一个股占比 25.0%，超过20%"],
        }
        with patch("views.sector_view.SectorService", return_value=mock_service):
            resp = client.get("/api/portfolio/sector/concentration")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data["data"]["warnings"]) == 1
        assert "单一个股占比" in data["data"]["warnings"][0]
        assert "25.0%" in data["data"]["warnings"][0]
