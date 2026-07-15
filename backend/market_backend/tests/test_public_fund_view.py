import json
from unittest.mock import MagicMock, patch


class TestGetOneRealTime:
    def test_returns_success(self, client):
        mock_service = MagicMock()
        mock_service.get_one_real_time.return_value = (
            [{"fund_code": "510050", "latest_price": 2.85}], None)
        with patch("views.public_fund_view.PublicFundService", return_value=mock_service):
            resp = client.post("/api/market/fund_public/real_time_get_one",
                               json={"platform": "eastmoney", "symbol": "ETF", "code": "510050"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert len(data["data"]) == 1

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
        mock_service.get_fund_name_list.assert_called_once_with(query="", limit=None)

    def test_passes_search_query_and_limit(self, client):
        mock_service = MagicMock()
        mock_service.get_fund_name_list.return_value = [
            {"fund_code": "000171", "fund_name": "易方达裕丰回报债券A"}
        ]
        with patch("views.public_fund_view.PublicFundService", return_value=mock_service):
            resp = client.get("/api/market/fund_public/fund_name_list?q=000171&limit=5")
        assert resp.status_code == 200
        mock_service.get_fund_name_list.assert_called_once_with(query="000171", limit=5)

    def test_rejects_invalid_search_limit(self, client):
        resp = client.get("/api/market/fund_public/fund_name_list?q=000171&limit=bad")
        assert resp.status_code == 400

    def test_no_params_needed(self, client):
        mock_service = MagicMock()
        mock_service.get_fund_name_list.return_value = []
        with patch("views.public_fund_view.PublicFundService", return_value=mock_service):
            resp = client.get("/api/market/fund_public/fund_name_list")
        assert resp.status_code == 200


# ===========================================================================
# Endpoints from individual_basic_info onwards
# ===========================================================================


class TestGetIndividualBasicInfo:
    def test_returns_success(self, client):
        mock_service = MagicMock()
        mock_service.get_fund_individual_basic_info.return_value = [{
            "fund_code": "000001", "fund_name": "华夏成长混合",
            "inception_date": "20010921", "latest_aum": "85.6亿",
            "fund_company": "华夏基金管理有限公司", "fund_manager": "张三",
        }]
        with patch("views.public_fund_view.PublicFundService", return_value=mock_service):
            resp = client.post("/api/market/fund_public/individual_basic_info",
                               json={"code": "000001"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert len(data["data"]) == 1
        assert data["data"][0]["fund_code"] == "000001"
        assert data["data"][0]["fund_name"] == "华夏成长混合"

    def test_missing_code(self, client):
        resp = client.post("/api/market/fund_public/individual_basic_info", json={})
        assert resp.status_code == 404
        data = json.loads(resp.data)
        assert data["message"] == "code is required"

    def test_empty_result(self, client):
        mock_service = MagicMock()
        mock_service.get_fund_individual_basic_info.return_value = []
        with patch("views.public_fund_view.PublicFundService", return_value=mock_service):
            resp = client.post("/api/market/fund_public/individual_basic_info",
                               json={"code": "000001"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert data["data"] == []


class TestGetIndividualDetailHold:
    def test_returns_success(self, client):
        mock_service = MagicMock()
        mock_service.get_fund_individual_detail_hold.return_value = [
            {"asset_type": "股票", "pct": "65.80%"},
            {"asset_type": "债券", "pct": "25.30%"},
        ]
        with patch("views.public_fund_view.PublicFundService", return_value=mock_service):
            resp = client.post("/api/market/fund_public/individual_detail_hold",
                               json={"code": "000001"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert len(data["data"]) == 2
        assert data["data"][0]["asset_type"] == "股票"

    def test_missing_code(self, client):
        resp = client.post("/api/market/fund_public/individual_detail_hold", json={})
        assert resp.status_code == 404
        data = json.loads(resp.data)
        assert data["message"] == "code is required"

    def test_with_optional_date(self, client):
        mock_service = MagicMock()
        mock_service.get_fund_individual_detail_hold.return_value = [
            {"asset_type": "股票", "pct": "65.80%"}
        ]
        with patch("views.public_fund_view.PublicFundService", return_value=mock_service):
            resp = client.post("/api/market/fund_public/individual_detail_hold",
                               json={"code": "000001", "date": "20260604"})
        assert resp.status_code == 200
        # Verify the service was called with the date
        mock_service.get_fund_individual_detail_hold.assert_called_once_with(
            code="000001", date="20260604")

    def test_empty_result(self, client):
        mock_service = MagicMock()
        mock_service.get_fund_individual_detail_hold.return_value = []
        with patch("views.public_fund_view.PublicFundService", return_value=mock_service):
            resp = client.post("/api/market/fund_public/individual_detail_hold",
                               json={"code": "000001"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["data"] == []


class TestGetPortfolioIndustryAllocation:
    def test_returns_success(self, client):
        mock_service = MagicMock()
        mock_service.get_fund_portfolio_industry_allocation_em.return_value = [
            {"sequence": 1, "industry_category": "制造业", "pct": "45.20",
             "market_value": "38.7亿", "as_of_date": "2025Q4"},
        ]
        with patch("views.public_fund_view.PublicFundService", return_value=mock_service):
            resp = client.post("/api/market/fund_public/portfolio_industry_allocation",
                               json={"code": "000001"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert len(data["data"]) == 1
        assert data["data"][0]["industry_category"] == "制造业"

    def test_missing_code(self, client):
        resp = client.post("/api/market/fund_public/portfolio_industry_allocation", json={})
        assert resp.status_code == 404
        data = json.loads(resp.data)
        assert data["message"] == "code is required"

    def test_with_optional_year(self, client):
        mock_service = MagicMock()
        mock_service.get_fund_portfolio_industry_allocation_em.return_value = []
        with patch("views.public_fund_view.PublicFundService", return_value=mock_service):
            resp = client.post("/api/market/fund_public/portfolio_industry_allocation",
                               json={"code": "000001", "year": "2025"})
        assert resp.status_code == 200
        mock_service.get_fund_portfolio_industry_allocation_em.assert_called_once_with(
            code="000001", year="2025")

    def test_empty_result(self, client):
        mock_service = MagicMock()
        mock_service.get_fund_portfolio_industry_allocation_em.return_value = []
        with patch("views.public_fund_view.PublicFundService", return_value=mock_service):
            resp = client.post("/api/market/fund_public/portfolio_industry_allocation",
                               json={"code": "000001"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["data"] == []


class TestGetPortfolioHoldStock:
    def test_returns_success(self, client):
        mock_service = MagicMock()
        mock_service.get_fund_portfolio_hold_stock.return_value = [
            {"sequence": 1, "stock_code": "600519", "stock_name": "贵州茅台",
             "pct": "9.85", "hold_shares": "120.5万", "hold_market_value": "21.6亿",
             "quarter": "2025Q4"},
        ]
        with patch("views.public_fund_view.PublicFundService", return_value=mock_service):
            resp = client.post("/api/market/fund_public/portfolio_hold_stock",
                               json={"code": "000001"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert len(data["data"]) == 1
        assert data["data"][0]["stock_code"] == "600519"
        assert data["data"][0]["stock_name"] == "贵州茅台"

    def test_missing_code(self, client):
        resp = client.post("/api/market/fund_public/portfolio_hold_stock", json={})
        assert resp.status_code == 404
        data = json.loads(resp.data)
        assert data["message"] == "code is required"

    def test_with_optional_year(self, client):
        mock_service = MagicMock()
        mock_service.get_fund_portfolio_hold_stock.return_value = []
        with patch("views.public_fund_view.PublicFundService", return_value=mock_service):
            resp = client.post("/api/market/fund_public/portfolio_hold_stock",
                               json={"code": "000001", "year": "2025"})
        assert resp.status_code == 200
        mock_service.get_fund_portfolio_hold_stock.assert_called_once_with(
            code="000001", year="2025")

    def test_empty_result(self, client):
        mock_service = MagicMock()
        mock_service.get_fund_portfolio_hold_stock.return_value = []
        with patch("views.public_fund_view.PublicFundService", return_value=mock_service):
            resp = client.post("/api/market/fund_public/portfolio_hold_stock",
                               json={"code": "000001"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["data"] == []


class TestGetPortfolioHoldBond:
    def test_returns_success(self, client):
        mock_service = MagicMock()
        mock_service.get_fund_portfolio_hold_bond.return_value = [
            {"sequence": 1, "bond_code": "200210", "bond_name": "20国开10",
             "pct": "5.20", "hold_market_value": "4.45亿", "quarter": "2025Q4"},
        ]
        with patch("views.public_fund_view.PublicFundService", return_value=mock_service):
            resp = client.post("/api/market/fund_public/portfolio_hold_bond",
                               json={"code": "000001"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["code"] == 200
        assert len(data["data"]) == 1
        assert data["data"][0]["bond_code"] == "200210"
        assert data["data"][0]["bond_name"] == "20国开10"

    def test_missing_code(self, client):
        resp = client.post("/api/market/fund_public/portfolio_hold_bond", json={})
        assert resp.status_code == 404
        data = json.loads(resp.data)
        assert data["message"] == "code is required"

    def test_with_optional_year(self, client):
        mock_service = MagicMock()
        mock_service.get_fund_portfolio_hold_bond.return_value = []
        with patch("views.public_fund_view.PublicFundService", return_value=mock_service):
            resp = client.post("/api/market/fund_public/portfolio_hold_bond",
                               json={"code": "000001", "year": "2025"})
        assert resp.status_code == 200
        mock_service.get_fund_portfolio_hold_bond.assert_called_once_with(
            code="000001", year="2025")

    def test_empty_result(self, client):
        mock_service = MagicMock()
        mock_service.get_fund_portfolio_hold_bond.return_value = []
        with patch("views.public_fund_view.PublicFundService", return_value=mock_service):
            resp = client.post("/api/market/fund_public/portfolio_hold_bond",
                               json={"code": "000001"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["data"] == []
