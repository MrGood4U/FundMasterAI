import json

import pandas as pd
from unittest.mock import MagicMock, patch

from apis.akshare_public_fund_api import (
    AksharePublicFund,
    _fund_portfolio_bond_hold_em,
    _fund_portfolio_hold_em,
)


class TestGetFundIndividualBasicInfo:
    def test_returns_single_row_after_transpose(self, sample_fund_individual_basic_info_raw_df):
        """API transposes item/value → single row, then maps columns."""
        api = AksharePublicFund()
        with patch("apis.akshare_public_fund_api.ak.fund_individual_basic_info_xq",
                   return_value=sample_fund_individual_basic_info_raw_df) as mock_ak:
            result = api.get_fund_individual_basic_info("000001")

        mock_ak.assert_called_once_with(symbol="000001")
        # After transpose + mapping: single row
        assert len(result) == 1

    def test_mapped_columns_present(self, sample_fund_individual_basic_info_raw_df):
        api = AksharePublicFund()
        with patch("apis.akshare_public_fund_api.ak.fund_individual_basic_info_xq",
                   return_value=sample_fund_individual_basic_info_raw_df):
            result = api.get_fund_individual_basic_info("000001")

        assert "fund_code" in result.columns
        assert "fund_name" in result.columns
        assert "inception_date" in result.columns
        assert "latest_aum" in result.columns
        assert "fund_company" in result.columns
        assert "fund_manager" in result.columns
        assert "custodian_bank" in result.columns
        assert "fund_type" in result.columns
        assert "rating_agency" in result.columns
        assert "fund_rating" in result.columns
        assert "investment_strategy" in result.columns
        assert "investment_objective" in result.columns

    def test_original_chinese_columns_removed(self, sample_fund_individual_basic_info_raw_df):
        api = AksharePublicFund()
        with patch("apis.akshare_public_fund_api.ak.fund_individual_basic_info_xq",
                   return_value=sample_fund_individual_basic_info_raw_df):
            result = api.get_fund_individual_basic_info("000001")

        assert "基金代码" not in result.columns
        assert "成立时间" not in result.columns
        assert "最新规模" not in result.columns
        assert "基金公司" not in result.columns
        assert "基金经理" not in result.columns

    def test_values_correct_after_transpose(self, sample_fund_individual_basic_info_raw_df):
        api = AksharePublicFund()
        with patch("apis.akshare_public_fund_api.ak.fund_individual_basic_info_xq",
                   return_value=sample_fund_individual_basic_info_raw_df):
            result = api.get_fund_individual_basic_info("000001")

        assert result.iloc[0]["fund_code"] == "000001"
        assert result.iloc[0]["fund_name"] == "华夏成长混合"
        assert result.iloc[0]["fund_company"] == "华夏基金管理有限公司"


class TestFundOpenFundRank:
    def test_lowercase_qdii_is_not_downgraded_to_all_funds(self):
        api = AksharePublicFund()
        upstream = pd.DataFrame([{
            "基金代码": "000834",
            "基金简称": "大成纳斯达克100ETF联接(QDII)A",
            "单位净值": 6.12,
            "日增长率": 0.45,
            "近1年": 18.2,
            "今年来": 9.1,
        }])

        with patch("apis.akshare_public_fund_api.ak.fund_open_fund_rank_em",
                   return_value=upstream) as mock_ak:
            result = api.fund_open_fund_rank("qdii", "change_1y")

        mock_ak.assert_called_once_with(symbol="QDII")
        assert result.iloc[0]["fund_code"] == "000834"
        assert result.iloc[0]["change_1y"] == 18.2


class TestGetFundIndividualDetailHold:
    def test_returns_mapped_dataframe(self, sample_fund_individual_detail_hold_raw_df):
        api = AksharePublicFund()
        with patch("apis.akshare_public_fund_api.ak.fund_individual_detail_hold_xq",
                   return_value=sample_fund_individual_detail_hold_raw_df) as mock_ak:
            result = api.get_fund_individual_detail_hold("000001", "20260604")

        mock_ak.assert_called_once_with(symbol="000001", date="20260604")
        assert len(result) == 3

    def test_mapped_columns_present(self, sample_fund_individual_detail_hold_raw_df):
        api = AksharePublicFund()
        with patch("apis.akshare_public_fund_api.ak.fund_individual_detail_hold_xq",
                   return_value=sample_fund_individual_detail_hold_raw_df):
            result = api.get_fund_individual_detail_hold("000001", "20260604")

        assert "asset_type" in result.columns
        assert "pct" in result.columns

    def test_original_chinese_columns_removed(self, sample_fund_individual_detail_hold_raw_df):
        api = AksharePublicFund()
        with patch("apis.akshare_public_fund_api.ak.fund_individual_detail_hold_xq",
                   return_value=sample_fund_individual_detail_hold_raw_df):
            result = api.get_fund_individual_detail_hold("000001", "20260604")

        assert "资产类型" not in result.columns
        assert "仓位占比" not in result.columns

    def test_returns_empty_dataframe_when_no_holdings(self):
        api = AksharePublicFund()
        with patch("apis.akshare_public_fund_api.ak.fund_individual_detail_hold_xq",
                   return_value=pd.DataFrame()):
            result = api.get_fund_individual_detail_hold("000001", "20260604")
        assert len(result) == 0


class TestGetFundPortfolioIndustryAllocationEm:
    def test_returns_mapped_dataframe(self, sample_portfolio_industry_allocation_raw_df):
        api = AksharePublicFund()
        with patch("apis.akshare_public_fund_api.ak.fund_portfolio_industry_allocation_em",
                   return_value=sample_portfolio_industry_allocation_raw_df) as mock_ak:
            result = api.get_fund_portfolio_industry_allocation_em("000001", "2025")

        mock_ak.assert_called_once_with(symbol="000001", date="2025")
        # Filtered to first date (2025Q4), so 2 rows
        assert len(result) == 2

    def test_filters_to_first_date_only(self, sample_portfolio_industry_allocation_raw_df):
        """Only rows matching the first date should be kept."""
        api = AksharePublicFund()
        with patch("apis.akshare_public_fund_api.ak.fund_portfolio_industry_allocation_em",
                   return_value=sample_portfolio_industry_allocation_raw_df):
            result = api.get_fund_portfolio_industry_allocation_em("000001", "2025")

        # All rows have the same 截止日期 (first date = "2025Q4")
        assert all(row["as_of_date"] == "2025Q4" for _, row in result.iterrows())

    def test_mapped_columns_present(self, sample_portfolio_industry_allocation_raw_df):
        api = AksharePublicFund()
        with patch("apis.akshare_public_fund_api.ak.fund_portfolio_industry_allocation_em",
                   return_value=sample_portfolio_industry_allocation_raw_df):
            result = api.get_fund_portfolio_industry_allocation_em("000001", "2025")

        assert "sequence" in result.columns
        assert "industry_category" in result.columns
        assert "pct" in result.columns
        assert "market_value" in result.columns
        assert "as_of_date" in result.columns

    def test_original_chinese_columns_removed(self, sample_portfolio_industry_allocation_raw_df):
        api = AksharePublicFund()
        with patch("apis.akshare_public_fund_api.ak.fund_portfolio_industry_allocation_em",
                   return_value=sample_portfolio_industry_allocation_raw_df):
            result = api.get_fund_portfolio_industry_allocation_em("000001", "2025")

        assert "序号" not in result.columns
        assert "行业类别" not in result.columns
        assert "占净值比例" not in result.columns

    def test_returns_empty_list_when_empty_dataframe(self):
        api = AksharePublicFund()
        with patch("apis.akshare_public_fund_api.ak.fund_portfolio_industry_allocation_em",
                   return_value=pd.DataFrame()):
            result = api.get_fund_portfolio_industry_allocation_em("000001", "2025")
        assert result == []


class TestGetFundPortfolioHoldStock:
    def test_sends_required_referer_and_short_timeout(self):
        html = """
        <div>
          <h4 class="t"><label><a>华夏成长混合</a>&nbsp;&nbsp;2026年1季度股票投资明细</label></h4>
          <table>
            <thead><tr>
              <th>序号</th><th>股票代码</th><th>股票名称</th><th>占净值 比例</th>
              <th>持股数（万股）</th><th>持仓市值（万元）</th><th>相关资讯</th>
            </tr></thead>
            <tbody><tr>
              <td>1</td><td>600519</td><td>贵州茅台</td><td>5.00%</td>
              <td>10.0</td><td>15000.0</td><td>-</td>
            </tr></tbody>
          </table>
        </div>
        """
        response = MagicMock()
        response.text = f"var apidata={json.dumps({'content': html}, ensure_ascii=False)};"

        with patch(
            "apis.akshare_public_fund_api.requests.get",
            return_value=response,
        ) as mock_get:
            result = _fund_portfolio_hold_em("000001", "2026")

        response.raise_for_status.assert_called_once_with()
        _, kwargs = mock_get.call_args
        assert kwargs["headers"] == {
            "Referer": "https://fundf10.eastmoney.com/ccmx_000001.html"
        }
        assert kwargs["timeout"] == 10
        assert result.iloc[0]["股票代码"] == "600519"
        assert result.iloc[0]["股票名称"] == "贵州茅台"

    def test_returns_mapped_dataframe(self, sample_portfolio_hold_stock_raw_df):
        api = AksharePublicFund()
        with patch("apis.akshare_public_fund_api._fund_portfolio_hold_em",
                   return_value=sample_portfolio_hold_stock_raw_df) as mock_ak:
            result = api.get_fund_portfolio_hold_stock("000001", "2025")

        mock_ak.assert_called_once_with(symbol="000001", date="2025")
        assert len(result) == 2

    def test_filters_to_first_date_only(self, sample_portfolio_hold_stock_raw_df):
        api = AksharePublicFund()
        with patch("apis.akshare_public_fund_api._fund_portfolio_hold_em",
                   return_value=sample_portfolio_hold_stock_raw_df):
            result = api.get_fund_portfolio_hold_stock("000001", "2025")

        assert all(row["quarter"] == "2025Q4" for _, row in result.iterrows())

    def test_mapped_columns_present(self, sample_portfolio_hold_stock_raw_df):
        api = AksharePublicFund()
        with patch("apis.akshare_public_fund_api._fund_portfolio_hold_em",
                   return_value=sample_portfolio_hold_stock_raw_df):
            result = api.get_fund_portfolio_hold_stock("000001", "2025")

        assert "sequence" in result.columns
        assert "stock_code" in result.columns
        assert "stock_name" in result.columns
        assert "pct" in result.columns
        assert "hold_shares" in result.columns
        assert "hold_market_value" in result.columns
        assert "quarter" in result.columns

    def test_original_chinese_columns_removed(self, sample_portfolio_hold_stock_raw_df):
        api = AksharePublicFund()
        with patch("apis.akshare_public_fund_api._fund_portfolio_hold_em",
                   return_value=sample_portfolio_hold_stock_raw_df):
            result = api.get_fund_portfolio_hold_stock("000001", "2025")

        assert "股票代码" not in result.columns
        assert "股票名称" not in result.columns
        assert "占净值比例" not in result.columns

    def test_returns_empty_list_when_empty_dataframe(self):
        api = AksharePublicFund()
        with patch("apis.akshare_public_fund_api._fund_portfolio_hold_em",
                   return_value=pd.DataFrame()):
            result = api.get_fund_portfolio_hold_stock("000001", "2025")
        assert result == []


class TestGetFundPortfolioHoldBond:
    def test_sends_required_referer_and_short_timeout(self):
        html = """
        <div>
          <h4 class="t">
            <label><a>债券基金</a>&nbsp;&nbsp;2026年1季度债券投资明细</label>
            <label>&nbsp;&nbsp;&nbsp;&nbsp;来源：天天基金&nbsp;&nbsp;&nbsp;&nbsp;截止至：2026-03-31</label>
          </h4>
          <table>
            <thead><tr>
              <th>序号</th><th>债券代码</th><th>债券名称</th><th>占净值比例</th>
              <th>持仓市值（万元）</th>
            </tr></thead>
            <tbody><tr>
              <td>1</td><td>240210</td><td>24国开10</td><td>18.59%</td>
              <td>138,564.80</td>
            </tr></tbody>
          </table>
        </div>
        """
        response = MagicMock()
        response.text = f"var apidata={json.dumps({'content': html}, ensure_ascii=False)};"

        with patch(
            "apis.akshare_public_fund_api.requests.get",
            return_value=response,
        ) as mock_get:
            result = _fund_portfolio_bond_hold_em("000001", "2026")

        response.raise_for_status.assert_called_once_with()
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["type"] == "zqcc"
        assert kwargs["headers"] == {
            "Referer": "https://fundf10.eastmoney.com/ccmx1_000001.html"
        }
        assert kwargs["timeout"] == 10
        assert result.iloc[0]["债券代码"] == "240210"
        assert result.iloc[0]["债券名称"] == "24国开10"
        assert result.iloc[0]["季度"] == "2026年1季度债券投资明细"

    def test_returns_mapped_dataframe(self, sample_portfolio_hold_bond_raw_df):
        api = AksharePublicFund()
        with patch("apis.akshare_public_fund_api._fund_portfolio_bond_hold_em",
                   return_value=sample_portfolio_hold_bond_raw_df) as mock_ak:
            result = api.get_fund_portfolio_hold_bond("000001", "2025")

        mock_ak.assert_called_once_with(symbol="000001", date="2025")
        assert len(result) == 2

    def test_filters_to_first_date_only(self, sample_portfolio_hold_bond_raw_df):
        api = AksharePublicFund()
        with patch("apis.akshare_public_fund_api._fund_portfolio_bond_hold_em",
                   return_value=sample_portfolio_hold_bond_raw_df):
            result = api.get_fund_portfolio_hold_bond("000001", "2025")

        assert all(row["quarter"] == "2025Q4" for _, row in result.iterrows())

    def test_mapped_columns_present(self, sample_portfolio_hold_bond_raw_df):
        api = AksharePublicFund()
        with patch("apis.akshare_public_fund_api._fund_portfolio_bond_hold_em",
                   return_value=sample_portfolio_hold_bond_raw_df):
            result = api.get_fund_portfolio_hold_bond("000001", "2025")

        assert "sequence" in result.columns
        assert "bond_code" in result.columns
        assert "bond_name" in result.columns
        assert "pct" in result.columns
        assert "hold_market_value" in result.columns
        assert "quarter" in result.columns

    def test_original_chinese_columns_removed(self, sample_portfolio_hold_bond_raw_df):
        api = AksharePublicFund()
        with patch("apis.akshare_public_fund_api._fund_portfolio_bond_hold_em",
                   return_value=sample_portfolio_hold_bond_raw_df):
            result = api.get_fund_portfolio_hold_bond("000001", "2025")

        assert "债券代码" not in result.columns
        assert "债券名称" not in result.columns
        assert "占净值比例" not in result.columns

    def test_returns_empty_list_when_empty_dataframe(self):
        api = AksharePublicFund()
        with patch("apis.akshare_public_fund_api._fund_portfolio_bond_hold_em",
                   return_value=pd.DataFrame()):
            result = api.get_fund_portfolio_hold_bond("000001", "2025")
        assert result == []
