"""
Chinese-to-English field name mappings for akshare API responses.
Each mapping corresponds to the DataFrame columns returned by a specific akshare function.
"""

import pandas as pd


def apply_mapping(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """Safely rename DataFrame columns using the mapping.

    Only renames columns that exist in the DataFrame. Columns not in the
    mapping pass through unchanged, and mapping entries not in the DataFrame
    are silently ignored.
    """
    rename_dict = {k: v for k, v in mapping.items() if k in df.columns}
    return df.rename(columns=rename_dict)

_CODE_NAME = {
    "基金代码": "fund_code",
    "代码": "fund_code",
    "基金名称": "fund_name",
    "名称": "fund_name",
}

FUND_ANNOUNCEMENT_FIELDS = {
    **_CODE_NAME,
    "公告标题": "announcement_title",
    "公告日期": "announcement_date",
    "报告ID": "report_id",
}

STOCK_NEWS_EM_FIELDS = {
    "关键词": "keyword",
    "新闻标题": "news_title",
    "新闻内容": "news_content",
    "发布时间": "publish_time",
    "文章来源": "source",
    "新闻链接": "url",
}