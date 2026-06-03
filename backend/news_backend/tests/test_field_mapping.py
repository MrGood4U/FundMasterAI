import pandas as pd
from apis.field_mapping import (
    apply_mapping,
    FUND_ANNOUNCEMENT_FIELDS,
    STOCK_NEWS_EM_FIELDS,
)


class TestApplyMapping:
    def test_renames_only_existing_columns(self):
        df = pd.DataFrame([{"关键词": "茅台", "发布时间": "2026-06-01"}])
        result = apply_mapping(df, STOCK_NEWS_EM_FIELDS)
        assert "keyword" in result.columns
        assert "publish_time" in result.columns
        assert "关键词" not in result.columns

    def test_ignores_mapping_entries_not_in_df(self):
        """Mapping entries for columns not in the DataFrame are silently ignored."""
        df = pd.DataFrame([{"关键词": "茅台"}])
        result = apply_mapping(df, STOCK_NEWS_EM_FIELDS)
        # Only 关键词 got renamed; other mapped columns weren't present
        assert "keyword" in result.columns
        assert "news_title" not in result.columns
        assert "news_content" not in result.columns

    def test_preserves_unmapped_columns(self):
        """Columns not in the mapping pass through unchanged."""
        df = pd.DataFrame([{
            "关键词": "茅台",
            "自定义字段": "保留原样",
        }])
        result = apply_mapping(df, STOCK_NEWS_EM_FIELDS)
        assert "keyword" in result.columns          # renamed
        assert "自定义字段" in result.columns        # unmapped → preserved

    def test_empty_dataframe_handles_gracefully(self):
        df = pd.DataFrame()
        result = apply_mapping(df, STOCK_NEWS_EM_FIELDS)
        assert result.empty

    def test_all_stock_news_fields_mapped(self, sample_stock_news_raw_df):
        result = apply_mapping(sample_stock_news_raw_df, STOCK_NEWS_EM_FIELDS)
        expected_cols = {"keyword", "news_title", "news_content",
                         "publish_time", "source", "url"}
        assert expected_cols.issubset(set(result.columns))

    def test_all_fund_announcement_fields_mapped(self, sample_fund_announcement_raw_df):
        result = apply_mapping(sample_fund_announcement_raw_df, FUND_ANNOUNCEMENT_FIELDS)
        expected_cols = {"fund_code", "fund_name", "announcement_title",
                         "announcement_date", "report_id"}
        assert expected_cols.issubset(set(result.columns))

    def test_code_and_name_mapped_correctly_via_code_name_dict(self):
        """_CODE_NAME dict maps both 基金代码→fund_code and 代码→fund_code."""
        df = pd.DataFrame([{
            "代码": "000001",
            "名称": "华夏成长",
            "公告标题": "测试公告",
            "公告日期": "2026-01-01",
            "报告ID": "999",
        }])
        result = apply_mapping(df, FUND_ANNOUNCEMENT_FIELDS)
        assert result.iloc[0]["fund_code"] == "000001"
        assert result.iloc[0]["fund_name"] == "华夏成长"
