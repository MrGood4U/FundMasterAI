import pytest
import pandas as pd

from app import create_app


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Sample DataFrames for mocking akshare API returns (raw Chinese column names)
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_stock_news_raw_df():
    """Simulates raw ak.stock_news_em() return with Chinese column names."""
    return pd.DataFrame([
        {
            "关键词": "贵州茅台",
            "新闻标题": "茅台发布2025年年报",
            "新闻内容": "贵州茅台发布2025年年报，营收同比增长15%",
            "发布时间": "2026-06-01 10:30:00",
            "文章来源": "东方财富",
            "新闻链接": "https://finance.eastmoney.com/a/xxx.html",
        },
        {
            "关键词": "贵州茅台",
            "新闻标题": "茅台宣布分红方案",
            "新闻内容": "贵州茅台公告2025年度分红方案",
            "发布时间": "2026-06-02 14:20:00",
            "文章来源": "证券时报",
            "新闻链接": "https://finance.eastmoney.com/a/yyy.html",
        },
    ])


@pytest.fixture
def sample_fund_announcement_raw_df():
    """Simulates raw ak.fund_announcement_dividend_em() return with Chinese column names."""
    return pd.DataFrame([
        {
            "基金代码": "000001",
            "基金名称": "华夏成长混合",
            "公告标题": "华夏成长混合2026年第一次分红公告",
            "公告日期": "2026-05-28",
            "报告ID": "1234567",
        },
        {
            "基金代码": "000001",
            "基金名称": "华夏成长混合",
            "公告标题": "华夏成长混合2025年第二次分红公告",
            "公告日期": "2025-11-15",
            "报告ID": "1234568",
        },
    ])


# ---------------------------------------------------------------------------
# Sample DataFrames — already mapped (simulate AkshareNews API return values)
# These have English column names after field_mapping has been applied.
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_stock_news_mapped_df():
    """Simulates AkshareNews.stock_news_recent() return (English column names)."""
    return pd.DataFrame([
        {
            "keyword": "贵州茅台",
            "news_title": "茅台发布2025年年报",
            "news_content": "贵州茅台发布2025年年报，营收同比增长15%",
            "publish_time": "2026-06-01 10:30:00",
            "source": "东方财富",
            "url": "https://finance.eastmoney.com/a/xxx.html",
        },
        {
            "keyword": "贵州茅台",
            "news_title": "茅台宣布分红方案",
            "news_content": "贵州茅台公告2025年度分红方案",
            "publish_time": "2026-06-02 14:20:00",
            "source": "证券时报",
            "url": "https://finance.eastmoney.com/a/yyy.html",
        },
    ])


@pytest.fixture
def sample_fund_announcement_mapped_df():
    """Simulates AkshareNews.public_fund_announcement() return (English column names)."""
    return pd.DataFrame([
        {
            "fund_code": "000001",
            "fund_name": "华夏成长混合",
            "announcement_title": "华夏成长混合2026年第一次分红公告",
            "announcement_date": "2026-05-28",
            "report_id": "1234567",
            "url": "https://fund.eastmoney.com/gonggao/000001,1234567.html",
        },
        {
            "fund_code": "000001",
            "fund_name": "华夏成长混合",
            "announcement_title": "华夏成长混合2025年第二次分红公告",
            "announcement_date": "2025-11-15",
            "report_id": "1234568",
            "url": "https://fund.eastmoney.com/gonggao/000001,1234568.html",
        },
    ])
