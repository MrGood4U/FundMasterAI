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


# ---------------------------------------------------------------------------
# Shared partials (used via **unpacking in the full mappings below)
# ---------------------------------------------------------------------------
_PRICE_FIELDS = {
    "最新价": "latest_price",
    "开盘": "open",
    "开盘价": "open",
    "收盘": "close",
    "收盘价": "close",
    "最高": "high",
    "最高价": "high",
    "最低": "low",
    "最低价": "low",
    "涨跌幅": "change_pct",
    "涨跌额": "change_amount",
    "成交量": "volume",
    "成交额": "turnover",
    "昨收": "prev_close",
}

_CODE_NAME = {
    "代码": "stock_code",
    "股票代码": "stock_code",
    "名称": "stock_name",
    "股票名称": "stock_name",
}

# ---------------------------------------------------------------------------
# Stock mappings
# ---------------------------------------------------------------------------

# ak.stock_zh_a_spot_em()  -- 东方财富 A 股实时行情
STOCK_SPOT_EM_MAP = {
    **_CODE_NAME,
    **_PRICE_FIELDS,
    "序号": "sequence",
    "今开": "open",
    "振幅": "amplitude",
    "量比": "volume_ratio",
    "换手率": "turnover_rate",
    "市盈率-动态": "pe_dynamic",
    "市净率": "pb",
    "总市值": "total_market_cap",
    "流通市值": "circulating_market_cap",
    "涨速": "rise_speed",
    "5分钟涨跌": "change_5min",
    "60日涨跌幅": "change_60d",
    "年初至今涨跌幅": "change_ytd",
}

# ak.stock_zh_a_hist()  -- 东方财富 A 股历史行情
STOCK_HIST_EM_MAP = {
    "日期": "date",
    **_CODE_NAME,
    **_PRICE_FIELDS,
    "振幅": "amplitude",
    "换手率": "turnover_rate",
}

# ak.stock_bid_ask_em()  -- 东方财富 A 股盘口 (applied AFTER pivot_table)
BID_ASK_EM_MAP = {
    "最新": "latest_price",
    "均价": "average_price",
    "涨幅": "change_pct",
    "涨跌": "change_amount",
    "总手": "total_volume",
    "金额": "turnover",
    "换手": "turnover_rate",
    "量比": "volume_ratio",
    "最高": "high",
    "最低": "low",
    "今开": "open",
    "昨收": "prev_close",
    "涨停": "upper_limit",
    "跌停": "lower_limit",
    "外盘": "bid_volume",
    "内盘": "ask_volume",
}

# ak.stock_zh_a_daily()  -- 新浪 A 股历史行情
# Columns are already in English: date, open, close, high, low, volume, etc.
STOCK_HIST_SINA_MAP = {}

# ---------------------------------------------------------------------------
# Public fund mappings
# ---------------------------------------------------------------------------

_FUND_CODE_NAME = {
    "基金代码": "fund_code",
    "代码": "fund_code",
    "基金名称": "fund_name",
    "名称": "fund_name",
    "基金全称": "fund_full_name",
    "全称": "fund_full_name",
}

# ak.fund_etf_spot_em()  -- 东方财富 ETF 实时行情
FUND_ETF_SPOT_EM_MAP = {
    **_FUND_CODE_NAME,
    **_PRICE_FIELDS,
    "IOPV实时估值": "iopv",
    "基金折价率": "discount_rate",
    "今开": "open",
    "昨收": "prev_close",
    "量比": "volume_ratio",
    "换手率": "turnover_rate",
    "委比": "order_ratio",
    "外盘": "bid_volume",
    "内盘": "ask_volume",
    "主力净流入-净额": "main_net_inflow_amount",
    "主力净流入-净占比": "main_net_inflow_pct",
    "超大单净流入-净额": "super_large_net_inflow_amount",
    "超大单净流入-净占比": "super_large_net_inflow",
    "大单净流入-净额": "large_net_inflow_amount",
    "大单净流入-净占比": "large_net_inflow_pct",
    "中单净流入-净额": "medium_net_inflow_amount",
    "中单净流入-净占比": "medium_net_inflow_pct",
    "小单净流入-净额": "small_net_inflow_amount",
    "小单净流入-净占比": "small_net_inflow_pct",
    "现手": "current_volume",
    "买一": "bid_price_1",
    "卖一": "ask_price_1",
    "最新份额": "latest_shares",
    "流通市值": "circulating_market_cap",
    "总市值": "total_market_cap",
    "数据日期": "data_date",
    "更新时间": "update_time",
}

# ak.fund_lof_spot_em()  -- 东方财富 LOF 实时行情
FUND_LOF_SPOT_EM_MAP = {
    **_FUND_CODE_NAME,
    **_PRICE_FIELDS,
    "换手率": "turnover_rate",
    "流通市值": "circulating_market_cap",
    "总市值": "total_market_cap",
}

# ak.fund_etf_hist_em() / ak.fund_lof_hist_em()  -- 东方财富基金日线历史
FUND_HIST_EM_MAP = {
    "日期": "date",
    **_PRICE_FIELDS,
    "振幅": "amplitude",
    "换手率": "turnover_rate",
}

# ak.fund_etf_hist_min_em() / ak.fund_lof_hist_min_em()  -- 东方财富基金分钟历史
FUND_HIST_MIN_EM_MAP = {
    "时间": "time",
    **_PRICE_FIELDS,
    "振幅": "amplitude",
    "换手率": "turnover_rate",
}

# ak.fund_etf_hist_sina()  -- 新浪 ETF 历史行情
# Columns are already in English: date, open, close, high, low, volume
FUND_HIST_SINA_MAP = {}

# ak.fund_etf_category_ths()  -- 同花顺基金分类
FUND_CATEGORY_THS_MAP = {
    "序号": "sequence",
    **_FUND_CODE_NAME,
    **_PRICE_FIELDS,
    "当前-单位净值": "current_unit_net_value",
    "当前-累计净值": "current_accumulated_net_value",
    "前一日-单位净值": "prev_unit_net_value",
    "前一日-累计净值": "prev_accumulated_net_value",
    "增长值": "growth_value",
    "增长率": "growth_rate",
    "赎回状态": "redemption_status",
    "申购状态": "subscription_status",
    "最新-交易日": "latest_trading_date",
    "最新-单位净值": "latest_unit_net_value",
    "最新-累计净值": "latest_accumulated_net_value",
    "基金类型": "fund_type",
    "查询日期": "query_date",
}

# ak.fund_etf_spot_sina()  -- 新浪基金实时行情
FUND_SPOT_SINA_MAP = {
    **_FUND_CODE_NAME,
    **_PRICE_FIELDS,
    "买入": "bid_price",
    "卖出": "ask_price",
    "今开": "open",
    "成交量": "volume",
    "成交额": "turnover",
}

# ---------------------------------------------------------------------------
# Index mappings
# ---------------------------------------------------------------------------

# ak.stock_zh_index_spot_em()  -- 东方财富指数实时行情
INDEX_SPOT_EM_MAP = {
    "序号": "sequence",
    "指数代码": "index_code",
    "指数名称": "index_name",
    **_PRICE_FIELDS,
    "今开": "open",
    "昨收": "prev_close",
}

# ak.stock_zh_index_daily_em()  -- 东方财富指数历史行情
# Columns come back as: date, open, close, high, low, volume, ...
# They are already in English for this akshare function, so map is minimal.
INDEX_HIST_EM_MAP = {}


# ak.fund_name_em()  -- 东方财富基金名称列表
FUND_NAME_EM_MAP = {
    "基金代码": "fund_code",
    "拼音缩写": "pinyin_abbr",
    "基金简称": "fund_name",
    "基金类型": "fund_type",
    "拼音全称": "pinyin_full",
}

# ak.fund_portfolio_hold_em()  -- 东方财富基金持仓股票
FUND_PORTFOLIO_HOLD_EM_MAP = {
    "序号": "sequence",
    "股票代码": "stock_code",
    "股票名称": "stock_name",
    "占净值比例": "net_value_pct",
    "持股数": "hold_shares",
    "持仓市值": "hold_market_value",
    "季度": "quarter",
}

# ak.fund_individual_analysis_xq()  -- 雪球基金个体分析
FUND_INDIVIDUAL_ANALYSIS_XQ_MAP = {
    "周期": "period",
    "较同类风险收益比": "risk_return_ratio_vs_peers",
    "较同类抗风险波动": "risk_robustness_vs_peers",
    "年化波动率": "annualized_volatility",
    "年化夏普比率": "annualized_sharpe_ratio",
    "最大回撤": "max_drawdown",
}

# ak.fund_individual_profit_probability_xq()  -- 雪球基金盈利概率
FUND_INDIVIDUAL_PROFIT_PROBABILITY_XQ_MAP = {
    "持有时长": "holding_period",
    "盈利概率": "profit_probability",
    "平均收益": "average_return",
}

# ak.fund_value_estimation_em()  -- 东方财富基金净值估算
FUND_VALUE_ESTIMATION_EM_MAP = {
    **_FUND_CODE_NAME,
    "序号": "sequence",
    "交易日-估算数据-估算值": "estimation_value",
    "交易日-估算数据-估算增长率": "estimation_growth_rate",
    "交易日-公布数据-单位净值": "reported_unit_net_value",
    "交易日-公布数据-日增长率": "reported_growth_rate",
    "估算偏差": "estimation_deviation_rate",
    "交易日-单位净值": "trading_day_unit_net_value"
}

# ak.fund_open_fund_rank_em()  -- 东方财富开放式基金排行榜
FUND_OPEN_FUND_RANK_EM_MAP = {
    **_FUND_CODE_NAME,
    "序号": "sequence",
    "日期": "date",
    "单位净值": "unit_net_value",
    "累计净值": "accumulated_net_value",
    "日增长率": "daily_growth_rate",
    "近1周": "change_1w",
    "近1月": "change_1m",
    "近3月": "change_3m",
    "近6月": "change_6m",
    "近1年": "change_1y",
    "近2年": "change_2y",
    "近3年": "change_3y",
    "今年来": "change_ytd",
    "成立来": "change_since_inception",
    "自定义": "custom",
    "手续费": "fee",
}

# ak.fund_info_index_em()  -- 东方财富基金信息指数
FUND_INFO_INDEX_EM_MAP = {
    **_FUND_CODE_NAME,
    "单位净值": "unit_net_value",
    "日期": "date",
    "日增长率": "daily_growth_rate",
    "近1周": "change_1w",
    "近1月": "change_1m",
    "近3月": "change_3m",
    "近6月": "change_6m",
    "近1年": "change_1y",
    "近2年": "change_2y",
    "近3年": "change_3y",
    "今年来": "change_ytd",
    "成立来": "change_since_inception",
    "手续费": "fee",
    "起购金额": "min_purchase_amount",
    "跟踪标的": "tracking_index",
    "跟踪方式": "tracking_method",
}

# ak.fund_individual_basic_info_xq()  -- 东方财富基金信息 (单独基金信息)
FUND_INDIVIDUAL_BASIC_INFO_MAP = {
    **_FUND_CODE_NAME,
    "成立时间": "inception_date",
    "最新规模": "latest_aum",
    "基金公司": "fund_company",
    "基金经理": "fund_manager",
    "托管银行": "custodian_bank",
    "基金类型": "fund_type",
    "评级机构": "rating_agency",
    "基金评级": "fund_rating",
    "投资策略": "investment_strategy",
    "投资目标": "investment_objective",
}

FUND_INDIVIDUAL_DETAIL_HOLD_MAP = {
    "资产类型": "asset_type",
    "仓位占比": "pct",
}

FUND_PORTFOLIO_INDUSTRY_ALLOCATION_EM_MAP = {
    "序号": "sequence",
    "行业类别": "industry_category",
    "占净值比例": "pct",
    "市值": "market_value",
    "截止日期": "as_of_date",
    "截止时间": "as_of_date",
}

FUND_PORTFOLIO_HOLD_STOCK_MAP = {
    "序号": "sequence", 
    "股票代码": "stock_code",
    "股票名称": "stock_name",
    "占净值比例": "pct",
    "持股数": "hold_shares",
    "持仓市值": "hold_market_value",
    "季度": "quarter",
}

FUND_PORTFOLIO_HOLD_BOND_MAP = {
    "序号": "sequence",
    "债券代码": "bond_code",
    "债券名称": "bond_name",
    "占净值比例": "pct",
    "持仓市值": "hold_market_value",
    "季度": "quarter",
}


FUND_QUOTE_HISTORY_MAP = {
    "日期": "date",
    "单位净值": "unit_net_value",
    "累计净值": "accumulated_net_value",
    "涨跌幅": "change_pct",
}

_BOND_INFO = {
    "债券简称": "bond_name",
    "债券代码": "bond_code",
}

BOND_SPOT_QUOTE_MAP = {
    **_BOND_INFO,
    "报价机构": "quote_institution",
    "买入净价": "buying_clean_price",
    "卖出净价": "selling_clean_price",
    "买入收益率": "buying_yield",
    "卖出收益率": "selling_yield",
}

BOND_SPOT_DEAL_MAP = {
    **_BOND_INFO,
    "成交净价": "deal_clean_price",
    "最新收益率": "latest_yield",
    "涨跌": "change",
    "加权收益率": "weighted_yield",
    "交易量": "volume",
}

BOND_INFO_SEARCH_MAP = {
    **_BOND_INFO,
    "发行人/受托机构": "issuer_or_trustee",
    "债券类型": "bond_type",
    "发行日期": "issue_date",
    "最新债项评级": "latest_bond_rating",
    "查询代码": "query_code",
}

BOND_CHINA_YIELD_MAP = {
    **_BOND_INFO,
    "曲线名称": "curve_name",
    "日期": "date",
    "3月": "yield_3m",
    "6月": "yield_6m",
    "1年": "yield_1y",
    "3年": "yield_3y",
    "5年": "yield_5y",
    "7年": "yield_7y",
    "10年": "yield_10y",
    "30年": "yield_30y",
}