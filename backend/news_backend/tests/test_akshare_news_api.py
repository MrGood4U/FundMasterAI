import pandas as pd
from unittest.mock import MagicMock, patch

from apis.akshare_news_api import AkshareNews


class TestStockNewsRecent:
    def test_returns_mapped_dataframe(self, sample_stock_news_raw_df):
        api = AkshareNews()
        with patch("apis.akshare_news_api.ak.stock_news_em",
                   return_value=sample_stock_news_raw_df) as mock_ak:
            result = api.stock_news_recent("600519")

        mock_ak.assert_called_once_with(symbol="600519")
        assert len(result) == 2
        assert "keyword" in result.columns
        assert "news_title" in result.columns
        assert "news_content" in result.columns
        assert "publish_time" in result.columns
        assert "source" in result.columns
        assert "url" in result.columns

    def test_original_chinese_columns_removed(self, sample_stock_news_raw_df):
        api = AkshareNews()
        with patch("apis.akshare_news_api.ak.stock_news_em",
                   return_value=sample_stock_news_raw_df):
            result = api.stock_news_recent("600519")
        # Chinese column names should be renamed away
        assert "关键词" not in result.columns
        assert "新闻标题" not in result.columns
        assert "发布时间" not in result.columns
        assert "文章来源" not in result.columns
        assert "新闻链接" not in result.columns

    def test_returns_empty_dataframe_when_no_news(self):
        api = AkshareNews()
        with patch("apis.akshare_news_api.ak.stock_news_em",
                   return_value=pd.DataFrame()):
            result = api.stock_news_recent("000001")
        assert len(result) == 0


class TestPublicFundAnnouncement:
    def test_returns_mapped_dataframe(self, sample_fund_announcement_raw_df):
        api = AkshareNews()
        with patch("apis.akshare_news_api.ak.fund_announcement_dividend_em",
                   return_value=sample_fund_announcement_raw_df) as mock_ak:
            result = api.public_fund_announcement("000001")

        mock_ak.assert_called_once_with(symbol="000001")
        assert len(result) == 2
        assert "fund_code" in result.columns
        assert "fund_name" in result.columns
        assert "announcement_title" in result.columns
        assert "announcement_date" in result.columns
        assert "report_id" in result.columns
        assert "url" in result.columns

    def test_url_is_generated_from_fund_code_and_report_id(self, sample_fund_announcement_raw_df):
        api = AkshareNews()
        with patch("apis.akshare_news_api.ak.fund_announcement_dividend_em",
                   return_value=sample_fund_announcement_raw_df):
            result = api.public_fund_announcement("000001")

        expected_url_template = "https://fund.eastmoney.com/gonggao/000001,1234567.html"
        assert result.iloc[0]["url"] == expected_url_template

    def test_original_chinese_columns_removed(self, sample_fund_announcement_raw_df):
        api = AkshareNews()
        with patch("apis.akshare_news_api.ak.fund_announcement_dividend_em",
                   return_value=sample_fund_announcement_raw_df):
            result = api.public_fund_announcement("000001")
        # Chinese column names should be renamed away
        assert "基金代码" not in result.columns
        assert "基金名称" not in result.columns
        assert "公告标题" not in result.columns
        assert "公告日期" not in result.columns
        assert "报告ID" not in result.columns

    def test_returns_empty_dataframe_when_no_announcements(self):
        api = AkshareNews()
        with patch("apis.akshare_news_api.ak.fund_announcement_dividend_em",
                   return_value=pd.DataFrame()):
            result = api.public_fund_announcement("000001")
        assert len(result) == 0
