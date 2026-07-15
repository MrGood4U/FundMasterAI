import logging
from datetime import datetime, timedelta
from io import StringIO

import akshare as ak
import pandas as pd
import numpy as np
import requests
from akshare.utils import demjson
from bs4 import BeautifulSoup
from flask import current_app

from apis.field_mapping import (
    apply_mapping,
    FUND_ETF_SPOT_EM_MAP,
    FUND_LOF_SPOT_EM_MAP,
    FUND_HIST_EM_MAP,
    FUND_HIST_MIN_EM_MAP,
    FUND_HIST_SINA_MAP,
    FUND_CATEGORY_THS_MAP,
    FUND_SPOT_SINA_MAP,
    FUND_NAME_EM_MAP,
    FUND_PORTFOLIO_HOLD_EM_MAP,
    FUND_INDIVIDUAL_ANALYSIS_XQ_MAP,
    FUND_INDIVIDUAL_PROFIT_PROBABILITY_XQ_MAP,
    FUND_VALUE_ESTIMATION_EM_MAP,
    FUND_OPEN_FUND_RANK_EM_MAP,
    FUND_INFO_INDEX_EM_MAP,
    FUND_INDIVIDUAL_BASIC_INFO_MAP,
    FUND_INDIVIDUAL_DETAIL_HOLD_MAP,
    FUND_PORTFOLIO_INDUSTRY_ALLOCATION_EM_MAP,
    FUND_PORTFOLIO_HOLD_STOCK_MAP,
    FUND_PORTFOLIO_HOLD_BOND_MAP,
)


_EASTMONEY_FUND_ARCHIVES_URL = (
    "https://fundf10.eastmoney.com/FundArchivesDatas.aspx"
)
_EASTMONEY_FUND_PORTFOLIO_TIMEOUT_SECONDS = 10


def _fund_portfolio_hold_em(symbol: str, date: str) -> pd.DataFrame:
    """Fetch Eastmoney fund stock holdings with the required page referer.

    AkShare 1.18.64 calls this endpoint without a Referer. Eastmoney now
    answers those requests with a synthetic 404 page, while the same request
    from its public fund page succeeds. Keep the workaround isolated here so
    it can be removed when AkShare ships an upstream fix.
    """
    response = requests.get(
        _EASTMONEY_FUND_ARCHIVES_URL,
        params={
            "type": "jjcc",
            "code": symbol,
            "topline": "10000",
            "year": date,
            "month": "",
            "rt": "0.913877030254846",
        },
        headers={
            "Referer": f"https://fundf10.eastmoney.com/ccmx_{symbol}.html",
        },
        timeout=_EASTMONEY_FUND_PORTFOLIO_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    data_text = response.text.strip()
    payload_start = data_text.find("{")
    payload_end = data_text.rfind(";")
    if payload_start < 0:
        raise ValueError("Eastmoney fund holdings response has no data payload")
    if payload_end <= payload_start:
        payload_end = len(data_text)
    data_json = demjson.decode(data_text[payload_start:payload_end])
    content = data_json.get("content", "")

    column_names = [
        "序号",
        "股票代码",
        "股票名称",
        "占净值比例",
        "持股数",
        "持仓市值",
        "季度",
    ]
    if not content:
        return pd.DataFrame(columns=column_names)

    soup = BeautifulSoup(content, features="lxml")
    quarter_labels = []
    for heading in soup.find_all(name="h4", attrs={"class": "t"}):
        heading_text = heading.get_text()
        parts = heading_text.split("\xa0\xa0", 1)
        quarter_labels.append(parts[1] if len(parts) == 2 else heading_text)

    tables = pd.read_html(StringIO(content), converters={"股票代码": str})
    frames = []
    for index, temp_df in enumerate(tables):
        if index >= len(quarter_labels):
            break
        if "相关资讯" in temp_df.columns:
            del temp_df["相关资讯"]
        temp_df.rename(
            columns={
                "占净值 比例": "占净值比例",
                "持股数（万股）": "持股数",
                "持股数 （万股）": "持股数",
                "持仓市值（万元）": "持仓市值",
                "持仓市值 （万元）": "持仓市值",
                "持仓市值（万元人民币）": "持仓市值",
                "持仓市值 （万元人民币）": "持仓市值",
            },
            inplace=True,
        )
        temp_df["占净值比例"] = (
            temp_df["占净值比例"].str.split("%", expand=True).iloc[:, 0]
        )
        temp_df["季度"] = quarter_labels[index]
        frames.append(temp_df[column_names])

    if not frames:
        return pd.DataFrame(columns=column_names)

    result = pd.concat(frames, ignore_index=True)
    result["占净值比例"] = pd.to_numeric(result["占净值比例"], errors="coerce")
    result["持股数"] = pd.to_numeric(result["持股数"], errors="coerce")
    result["持仓市值"] = pd.to_numeric(result["持仓市值"], errors="coerce")
    result["序号"] = range(1, len(result) + 1)
    return result[column_names]


class AksharePublicFund:
    def eastmoney_real_time(self, symbol: str):
        if symbol == "ETF":
            return apply_mapping(ak.fund_etf_spot_em(), FUND_ETF_SPOT_EM_MAP)
        elif symbol == "LOF":
            return apply_mapping(ak.fund_lof_spot_em(), FUND_LOF_SPOT_EM_MAP)
        return None

    def eastmoney_hist_min(self, symbol: str, code: str, start_date: str, end_date: str, period: str, adjust: str):
        adjusts = ['', 'qfq', 'hfq']
        if adjust not in adjusts:
            adjust = 'hfq'

        periods = ['1', '5', '15', '30', '60']
        if period not in periods:
            return None

        symbols = ['ETF', 'LOF']
        if symbol not in symbols:
            return None

        if symbol == "ETF":
            df = ak.fund_etf_hist_min_em(symbol=code, period=period, adjust=adjust, start_date=start_date, end_date=end_date)
        elif symbol == "LOF":
            df = ak.fund_lof_hist_min_em(symbol=code, period=period, adjust=adjust, start_date=start_date, end_date=end_date)
        else:
            return None
        return apply_mapping(df, FUND_HIST_MIN_EM_MAP)

    def eastmoney_hist(self, symbol: str, code: str, start_date: str, end_date: str, period: str, adjust: str):
        adjusts = ['', 'qfq', 'hfq']
        if adjust not in adjusts:
            return None

        periods = ['daily', 'weekly', 'monthly']
        if period not in periods:
            return None

        symbols = ['ETF', 'LOF']
        if symbol not in symbols:
            return None

        if symbol == "ETF":
            df = ak.fund_etf_hist_em(symbol=code, period=period, adjust=adjust, start_date=start_date, end_date=end_date)
        elif symbol == "LOF":
            df = ak.fund_lof_hist_em(symbol=code, period=period, adjust=adjust, start_date=start_date, end_date=end_date)
        else:
            return None
        return apply_mapping(df, FUND_HIST_EM_MAP)

    def sina_hist(self, code: str, start_date: str, end_date: str):
        result = ak.fund_etf_hist_sina(symbol=code)
        result = apply_mapping(result, FUND_HIST_SINA_MAP)
        mask = (result["date"] >= pd.to_datetime(start_date)) & (result["date"] <= pd.to_datetime(end_date))
        result = result.loc[mask]
        return result

    def tonghuashun_real_time(self, symbol: str):
        tonghuashun_symbol_map = {
            "stock": "股票型",
            "bond": "债券型",
            "mixed": "混合型",
            "ETF": "ETF",
            "LOF": "LOF",
            "QDII": "QDII",
            "guaranteed": "保本型",
            "index": "指数型",
            "all": "",
        }
        if symbol not in tonghuashun_symbol_map:
            symbol = "all"
        symbol = tonghuashun_symbol_map[symbol]

        # Try progressively earlier dates to handle non-trading days
        # (weekends / holidays) where the upstream API returns empty data.
        _log = logging.getLogger(__name__)
        for offset in range(7):
            date_str = (datetime.now() - timedelta(days=offset)).strftime("%Y%m%d")
            try:
                df = ak.fund_etf_category_ths(symbol=symbol, date=date_str)
                if offset > 0:
                    _log.info(
                        "tonghuashun_real_time: fell back to %s (offset=%d)",
                        date_str, offset,
                    )
                return apply_mapping(df, FUND_CATEGORY_THS_MAP)
            except Exception:
                _log.warning(
                    "tonghuashun_real_time: %s failed, retrying...", date_str
                )
        _log.error("tonghuashun_real_time: all 7 attempts failed")
        return None

    def sina_real_time(self, symbol: str):
        sina_symbol_map = {
            "closed_end": "封闭式基金",
            "ETF": "ETF基金",
            "LOF": "LOF基金",
        }
        if symbol not in sina_symbol_map:
            return None
        df = ak.fund_etf_category_sina(symbol=symbol)
        return apply_mapping(df, FUND_SPOT_SINA_MAP)

    def real_time(self, symbol: str, platform: str):
        if platform == "eastmoney":
            return self.eastmoney_real_time(symbol)
        elif platform == "tonghuashun":
            return self.tonghuashun_real_time(symbol)
        elif platform == "sina":
            return self.sina_real_time(symbol)
        else:
            return self.tonghuashun_real_time(symbol)

    def hist_min(self, symbol: str, platform: str, code: str, start_date: str, end_date: str, period: str, adjust: str):
        if platform == "eastmoney":
            return self.eastmoney_hist_min(symbol, code, start_date, end_date, period, adjust)
        else:
            return None

    def hist(self, symbol: str, platform: str, code: str, start_date: str, end_date: str, period: str, adjust: str):
        if platform == "eastmoney":
            return self.eastmoney_hist(symbol, code, start_date, end_date, period, adjust)
        elif platform == 'sina':
            return self.sina_hist(code, start_date, end_date)
        else:
            return None

    def get_fund_name_list(self):
        df = ak.fund_name_em()
        return apply_mapping(df, FUND_NAME_EM_MAP)

    def get_fund_portfolio_holds(self, code: str, year: str):
        df = _fund_portfolio_hold_em(symbol=code, date=year)
        return apply_mapping(df, FUND_PORTFOLIO_HOLD_EM_MAP)

    def get_fund_individual_analysis(self, code: str):
        df = ak.fund_individual_analysis_xq(symbol=code)
        return apply_mapping(df, FUND_INDIVIDUAL_ANALYSIS_XQ_MAP)
    
    def get_fund_individual_profit_probability(self, code: str):
        df = ak.fund_individual_profit_probability_xq(symbol=code)
        return apply_mapping(df, FUND_INDIVIDUAL_PROFIT_PROBABILITY_XQ_MAP)

    def get_fund_value_estimation_list(self, symbol: str):
        symbol_map = {
            'all': '全部',
            'stock': '股票型',
            'mixed': '混合型',
            'bond': '债券型',
            'index': '指数型',
            'qdii': 'QDII',
            'etf_link': 'ETF联接',
            'lof': 'LOF',
            'exchange_traded_fund': '场内交易基金',
        }
        if symbol not in symbol_map:
            symbol = 'all'
        symbol = symbol_map[symbol]
        df = ak.fund_value_estimation_em(symbol=symbol)
        return apply_mapping(df, FUND_VALUE_ESTIMATION_EM_MAP)

    def fund_open_fund_rank(self, fund_type: str, order_by: str):
        fund_type = str(fund_type or "all").strip().lower()
        fund_type_set_map = {
            "all": "全部",
            "stock": "股票型",
            "mixed": "混合型",
            "bond": "债券型",
            "index": "指数型",
            "qdii": "QDII",
            "fof": "FOF",
        }
        if fund_type not in fund_type_set_map:
            fund_type = "all"
        fund_type = fund_type_set_map[fund_type]
        df = ak.fund_open_fund_rank_em(symbol=fund_type)
        df = df.replace([np.nan, np.inf, -np.inf, pd.NaT], None)
        df = df.replace([float('inf'), float('-inf')], None)
        df = apply_mapping(df, FUND_OPEN_FUND_RANK_EM_MAP)
        if "基金简称" in df.columns:
            df["fund_short_name"] = df["基金简称"].str.strip().str.replace("\n", "")

        # Sort by order_by column if it exists, otherwise default to "change_1y"
        if order_by not in df.columns:
            order_by = "change_1y"
        df = df.sort_values(by=order_by, ascending=False)
        return df
    
    # 指数基金信息(全部/沪深指数/行业主题/大盘指数/中盘指数/小盘指数/股票指数/债券指数) -- 东方财富
    def get_fund_info_index(self, symbol: str, indicator: str):
        symbol_map = {
            "all": "全部",
            "hs_index": "沪深指数",
            "industry_theme": "行业主题",
            "large_cap_index": "大盘指数",
            "mid_cap_index": "中盘指数",
            "small_cap_index": "小盘指数",
            "stock_index": "股票指数",
            "bond_index": "债券指数",
        }

        if symbol not in symbol_map:
            symbol = "all"

        symbol = symbol_map[symbol]

        indicator_map = {
            "all": "全部",
            "passive": "被动指数型",
            "enhanced": "增强指数型",
        }

        if indicator not in indicator_map:
            indicator = "all"

        indicator = indicator_map[indicator]

        df = ak.fund_info_index_em(symbol=symbol, indicator=indicator)

        return apply_mapping(df, FUND_INFO_INDEX_EM_MAP)
    
    # 单独基金信息
    def get_fund_individual_basic_info(self, code: str):
        old_df = ak.fund_individual_basic_info_xq(symbol=code)
        df = old_df.set_index("item").T
        df = df.reset_index(drop=True)
        df.columns.name = None
        return apply_mapping(df, FUND_INDIVIDUAL_BASIC_INFO_MAP)
    
    def get_fund_individual_detail_hold(self, code: str, date: str):
        df = ak.fund_individual_detail_hold_xq(symbol=code, date=date)
        return apply_mapping(df, FUND_INDIVIDUAL_DETAIL_HOLD_MAP)
    
    # 资产配置只暴露一年中最新的组成数据
    def get_fund_portfolio_industry_allocation_em(self, code:str, year: str):
        df = ak.fund_portfolio_industry_allocation_em(symbol=code, date=year)
        if df is None or df.empty:
            return []
        first_date = df.iloc[0]["截止时间"]
        df = df[df["截止时间"] == first_date]
        return apply_mapping(df, FUND_PORTFOLIO_INDUSTRY_ALLOCATION_EM_MAP)

    def get_fund_portfolio_hold_stock(self, code: str, year: str):
        df = _fund_portfolio_hold_em(symbol=code, date=year)
        if df is None or df.empty:
            return []
        first_date = df.iloc[0]["季度"]
        df = df[df["季度"] == first_date]
        return apply_mapping(df, FUND_PORTFOLIO_HOLD_STOCK_MAP)
    
    def get_fund_portfolio_hold_bond(self, code: str, year: str):
        df = ak.fund_portfolio_bond_hold_em(symbol=code, date=year)
        if df is None or df.empty:
            return []
        first_date = df.iloc[0]["季度"]
        df = df[df["季度"] == first_date]
        return apply_mapping(df, FUND_PORTFOLIO_HOLD_BOND_MAP)
