from unittest.mock import MagicMock

from services.news_service import NewsService


class TestGetStockRecentNews:
    def test_returns_list_of_dicts(self, sample_stock_news_mapped_df):
        service = NewsService()
        service.news_api.stock_news_recent = MagicMock(
            return_value=sample_stock_news_mapped_df)

        result = service.get_stock_recent_news("600519")

        service.news_api.stock_news_recent.assert_called_once_with("600519")
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["news_title"] == "茅台发布2025年年报"
        assert result[0]["keyword"] == "贵州茅台"
        assert result[0]["source"] == "东方财富"

    def test_returns_empty_list_when_no_news(self):
        import pandas as pd
        service = NewsService()
        service.news_api.stock_news_recent = MagicMock(return_value=pd.DataFrame())

        result = service.get_stock_recent_news("000001")
        assert result == []


class TestGetPublicFundAnnouncement:
    def test_returns_list_of_dicts(self, sample_fund_announcement_mapped_df):
        service = NewsService()
        service.news_api.public_fund_announcement = MagicMock(
            return_value=sample_fund_announcement_mapped_df)

        result = service.get_public_fund_announcement("000001")

        service.news_api.public_fund_announcement.assert_called_once_with("000001")
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["fund_name"] == "华夏成长混合"
        assert result[0]["announcement_title"] == "华夏成长混合2026年第一次分红公告"

    def test_returns_url_in_result(self, sample_fund_announcement_mapped_df):
        service = NewsService()
        service.news_api.public_fund_announcement = MagicMock(
            return_value=sample_fund_announcement_mapped_df)

        result = service.get_public_fund_announcement("000001")
        assert "url" in result[0]
        assert result[0]["url"] == "https://fund.eastmoney.com/gonggao/000001,1234567.html"

    def test_returns_empty_list_when_no_announcements(self):
        import pandas as pd
        service = NewsService()
        service.news_api.public_fund_announcement = MagicMock(return_value=pd.DataFrame())

        result = service.get_public_fund_announcement("000001")
        assert result == []
