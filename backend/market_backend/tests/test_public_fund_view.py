import json
from unittest.mock import MagicMock, patch


class TestGetOneRealTime:
    def test_returns_success(self, client):
        mock_service = MagicMock()
        mock_service.get_one_real_time.return_value = [{"fund_code": "510050", "latest_price": 2.85}]
        with patch("views.public_fund_view.PublicFundService", return_value=mock_service):
            resp = client.post("/api/market/fund_public/real_time_get_one",
                               json={"platform": "eastmoney", "symbol": "ETF", "code": "510050"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert len(data["data"]) == 1

    def test_missing_json_body(self, client):
        resp = client.post("/api/market/fund_public/real_time_get_one", data=None)
        assert resp.status_code == 404

    def test_missing_platform(self, client):
        resp = client.post("/api/market/fund_public/real_time_get_one",
                           json={"symbol": "ETF", "code": "510050"})
        assert resp.status_code == 404

    def test_missing_symbol(self, client):
        resp = client.post("/api/market/fund_public/real_time_get_one",
                           json={"platform": "eastmoney", "code": "510050"})
        assert resp.status_code == 404

    def test_missing_name_and_code(self, client):
        resp = client.post("/api/market/fund_public/real_time_get_one",
                           json={"platform": "eastmoney", "symbol": "ETF"})
        assert resp.status_code == 404


class TestGetAllRealTime:
    def test_returns_success(self, client):
        mock_service = MagicMock()
        mock_service.get_all_real_time.return_value = [
            {"fund_code": "510050"}, {"fund_code": "510300"}
        ]
        with patch("views.public_fund_view.PublicFundService", return_value=mock_service):
            resp = client.post("/api/market/fund_public/real_time_get_all",
                               json={"platform": "eastmoney", "symbol": "ETF"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert len(data["data"]) == 2

    def test_missing_json_body(self, client):
        resp = client.post("/api/market/fund_public/real_time_get_all", data=None)
        assert resp.status_code == 404


class TestGetHist:
    def test_returns_success(self, client):
        mock_service = MagicMock()
        mock_service.get_hist.return_value = [{"date": "2026-05-20", "close": 2.85}]
        with patch("views.public_fund_view.PublicFundService", return_value=mock_service):
            resp = client.post("/api/market/fund_public/hist",
                               json={"platform": "eastmoney", "symbol": "ETF",
                                     "code": "510050", "start_date": "2026-05-01",
                                     "end_date": "2026-05-28"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200

    def test_missing_platform(self, client):
        resp = client.post("/api/market/fund_public/hist",
                           json={"symbol": "ETF"})
        assert resp.status_code == 404


class TestGetHistMin:
    def test_returns_success(self, client):
        mock_service = MagicMock()
        mock_service.get_hist_min.return_value = [{"time": "09:30", "close": 2.85}]
        with patch("views.public_fund_view.PublicFundService", return_value=mock_service):
            resp = client.post("/api/market/fund_public/hist_min",
                               json={"platform": "eastmoney", "code": "510050",
                                     "symbol": "ETF", "start_date": "2026-05-28",
                                     "end_date": "2026-05-28", "period": "5"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200

    def test_missing_code(self, client):
        resp = client.post("/api/market/fund_public/hist_min",
                           json={"platform": "eastmoney"})
        assert resp.status_code == 404


class TestGetFundNameList:
    def test_returns_success(self, client):
        mock_service = MagicMock()
        mock_service.get_fund_name_list.return_value = [
            {"fund_code": "510050", "fund_name": "华夏上证50ETF"}
        ]
        with patch("views.public_fund_view.PublicFundService", return_value=mock_service):
            resp = client.get("/api/market/fund_public/fund_name_list")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert len(data["data"]) == 1

    def test_no_params_needed(self, client):
        mock_service = MagicMock()
        mock_service.get_fund_name_list.return_value = []
        with patch("views.public_fund_view.PublicFundService", return_value=mock_service):
            resp = client.get("/api/market/fund_public/fund_name_list")
        assert resp.status_code == 200
