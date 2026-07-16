import json
from unittest.mock import MagicMock, patch


class TestGetStockRecentNews:
    def test_returns_success(self, client):
        mock_service = MagicMock()
        mock_service.get_stock_recent_news.return_value = [
            {"keyword": "贵州茅台", "news_title": "茅台发布2025年年报",
             "news_content": "...", "publish_time": "2026-06-01 10:30:00",
             "source": "东方财富", "url": "https://..."},
        ]
        with patch("views.news_view.NewsService", return_value=mock_service):
            resp = client.post("/api/news/stock/get_recent_news",
                               json={"symbol": "600519"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert len(data["data"]) == 1
        assert data["data"][0]["keyword"] == "贵州茅台"

    def test_missing_symbol(self, client):
        resp = client.post("/api/news/stock/get_recent_news", json={})
        assert resp.status_code == 404
        data = json.loads(resp.data)
        assert data["message"] == "args not found"

    def test_empty_result(self, client):
        mock_service = MagicMock()
        mock_service.get_stock_recent_news.return_value = []
        with patch("views.news_view.NewsService", return_value=mock_service):
            resp = client.post("/api/news/stock/get_recent_news",
                               json={"symbol": "000001"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert data["data"] == []


class TestGetPublicFundAnnouncement:
    def test_returns_success(self, client):
        mock_service = MagicMock()
        mock_service.get_public_fund_announcement.return_value = [
            {"fund_code": "000001", "fund_name": "华夏成长混合",
             "announcement_title": "华夏成长混合2026年第一次分红公告",
             "announcement_date": "2026-05-28", "report_id": "1234567",
             "url": "https://fund.eastmoney.com/gonggao/000001,1234567.html"},
        ]
        with patch("views.news_view.NewsService", return_value=mock_service):
            resp = client.post("/api/news/public_fund/get_announcement",
                               json={"code": "000001"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert len(data["data"]) == 1
        assert data["data"][0]["fund_name"] == "华夏成长混合"

    def test_missing_code(self, client):
        resp = client.post("/api/news/public_fund/get_announcement", json={})
        assert resp.status_code == 404
        data = json.loads(resp.data)
        assert data["message"] == "args not found"

    def test_empty_result(self, client):
        mock_service = MagicMock()
        mock_service.get_public_fund_announcement.return_value = []
        with patch("views.news_view.NewsService", return_value=mock_service):
            resp = client.post("/api/news/public_fund/get_announcement",
                               json={"code": "000001"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert data["data"] == []
