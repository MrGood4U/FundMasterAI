from datetime import datetime
import akshare as ak
import pandas as pd
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
)


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
        today = datetime.now().strftime("%Y%m%d")
        df = ak.fund_etf_category_ths(symbol=symbol, date=today)
        return apply_mapping(df, FUND_CATEGORY_THS_MAP)

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
        df = ak.fund_portfolio_hold_em(symbol=code, date=year)
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

    def fund_open_fund_rank(self, fund_type: str):
        fund_type_set = ["all", "stock", "mixed", "stock", "index", "QDII", "FOF"]
        if fund_type not in fund_type_set:
            fund_type = "all"
        fund_type_set_map = {
            "all": "全部",
            "stock": "股票型",
            "mixed": "混合型",
            "bond": "债券型",
            "index": "指数型",
            "qdii": "QDII",
            "fof": "FOF",
        }
        fund_type = fund_type_set_map[fund_type]
        df = ak.fund_open_fund_rank_em(symbol=fund_type)
        return apply_mapping(df, FUND_OPEN_FUND_RANK_EM_MAP)
    
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