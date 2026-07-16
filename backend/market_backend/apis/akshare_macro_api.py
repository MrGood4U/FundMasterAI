"""
宏观数据 API — 基于 akshare，按国家（country）分发。

每个指标注册项包含:
    func    — akshare 函数引用
    name    — 中文名称
    desc    — 指标说明（面向前端展示）
    columns — 输出字段说明: {英文key: {"name": "中文列名", "desc": "含义"}}
    extra   — 可选额外参数及其默认值

前端调用流程:
    1. /macro/indicators  → 浏览有哪些指标
    2. /macro/schema      → 查看某个指标的字段定义（方便渲染表格/图表）
    3. /macro/data        → 获取实际数据
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

import akshare as ak
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 类型
# ---------------------------------------------------------------------------

_ColumnSpec = Dict[str, Any]  # {"name": "中文列名", "desc": "字段含义"}
_IndicatorEntry = Dict[str, Any]
_ColumnMap = Dict[str, _ColumnSpec]


# ---------------------------------------------------------------------------
# 注册表  ——  按 国家 → 指标 key → {func, name, desc, columns, extra}
# ---------------------------------------------------------------------------

_REGISTRY: Dict[str, Dict[str, _IndicatorEntry]] = {
    # ======================================================================
    # 中国
    # ======================================================================
    "china": {
        # -- 价格 -----------------------------------------------------------
        "cpi": {
            "func": ak.macro_china_cpi,
            "name": "居民消费价格指数(CPI)",
            "desc": "月度CPI数据，包含全国/城市/农村的当月值、同比、环比、累计值",
            "columns": {
                "month":              {"name": "月份",             "desc": "数据所属月份"},
                "national_value":     {"name": "全国-当月",         "desc": "全国CPI当月值（上年同月=100）"},
                "national_yoy":       {"name": "全国-同比增长",     "desc": "全国CPI同比增长率(%)"},
                "national_mom":       {"name": "全国-环比增长",     "desc": "全国CPI环比增长率(%)"},
                "national_cumulative":{"name": "全国-累计",         "desc": "全国CPI累计值"},
                "urban_value":        {"name": "城市-当月",         "desc": "城市CPI当月值"},
                "urban_yoy":          {"name": "城市-同比增长",     "desc": "城市CPI同比增长率(%)"},
                "urban_mom":          {"name": "城市-环比增长",     "desc": "城市CPI环比增长率(%)"},
                "urban_cumulative":   {"name": "城市-累计",         "desc": "城市CPI累计值"},
                "rural_value":        {"name": "农村-当月",         "desc": "农村CPI当月值"},
                "rural_yoy":          {"name": "农村-同比增长",     "desc": "农村CPI同比增长率(%)"},
                "rural_mom":          {"name": "农村-环比增长",     "desc": "农村CPI环比增长率(%)"},
                "rural_cumulative":   {"name": "农村-累计",         "desc": "农村CPI累计值"},
            },
        },
        "cpi_monthly": {
            "func": ak.macro_china_cpi_monthly,
            "name": "CPI月度报告",
            "desc": "统计局月度CPI详细报告",
        },
        "cpi_yearly": {
            "func": ak.macro_china_cpi_yearly,
            "name": "CPI年度报告",
            "desc": "统计局年度CPI报告",
        },
        "ppi": {
            "func": ak.macro_china_ppi,
            "name": "工业生产者出厂价格(PPI)",
            "desc": "月度PPI，反映工业品出厂价格变动趋势",
            "columns": {
                "month":             {"name": "月份",              "desc": "数据所属月份"},
                "ppi_value":         {"name": "当月-当月",          "desc": "PPI当月值"},
                "ppi_yoy":           {"name": "当月-同比增长",      "desc": "PPI同比增长率(%)"},
                "ppi_mom":           {"name": "当月-环比增长",      "desc": "PPI环比增长率(%)"},
                "ppi_cumulative":    {"name": "当月-累计",          "desc": "PPI累计值"},
            },
        },
        "ppi_yearly": {
            "func": ak.macro_china_ppi_yearly,
            "name": "PPI年度",
            "desc": "年度PPI数据",
        },
        # -- 增长 -----------------------------------------------------------
        "gdp": {
            "func": ak.macro_china_gdp,
            "name": "国内生产总值(GDP)",
            "desc": "季度GDP，含总量与分产业数据",
            "columns": {
                "quarter":            {"name": "季度",               "desc": "数据所属季度"},
                "gdp":                {"name": "国内生产总值-绝对值",  "desc": "GDP绝对值(亿元)"},
                "gdp_yoy":            {"name": "国内生产总值-同比增长","desc": "GDP同比增长率(%)"},
                "primary_industry":   {"name": "第一产业-绝对值",     "desc": "第一产业增加值(亿元)"},
                "primary_yoy":        {"name": "第一产业-同比增长",   "desc": "第一产业同比增长率(%)"},
                "secondary_industry": {"name": "第二产业-绝对值",     "desc": "第二产业增加值(亿元)"},
                "secondary_yoy":      {"name": "第二产业-同比增长",   "desc": "第二产业同比增长率(%)"},
                "tertiary_industry":  {"name": "第三产业-绝对值",     "desc": "第三产业增加值(亿元)"},
                "tertiary_yoy":       {"name": "第三产业-同比增长",   "desc": "第三产业同比增长率(%)"},
            },
        },
        "gdp_yearly": {
            "func": ak.macro_china_gdp_yearly,
            "name": "GDP年率",
            "desc": "年度GDP增长率，含预测值和前值",
            "columns": {
                "product":  {"name": "商品",  "desc": "指标名称"},
                "date":     {"name": "日期",  "desc": "发布日期"},
                "value":    {"name": "今值",  "desc": "本期实际值"},
                "forecast": {"name": "预测值","desc": "市场预测值"},
                "previous": {"name": "前值",  "desc": "上一期实际值"},
            },
        },
        "industrial_production": {
            "func": ak.macro_china_industrial_production_yoy,
            "name": "工业增加值同比",
            "desc": "规模以上工业增加值同比增长率",
        },
        # -- PMI ------------------------------------------------------------
        "pmi": {
            "func": ak.macro_china_pmi,
            "name": "采购经理人指数(PMI)",
            "desc": "月度PMI，含制造业和非制造业指数",
            "columns": {
                "month":                {"name": "月份",                "desc": "数据月份"},
                "manufacturing_index":  {"name": "制造业-指数",          "desc": "制造业PMI指数"},
                "manufacturing_yoy":    {"name": "制造业-同比增长",      "desc": "制造业PMI同比(%)"},
                "non_manufacturing_index":{"name": "非制造业-指数",      "desc": "非制造业PMI指数"},
                "non_manufacturing_yoy":{"name": "非制造业-同比增长",    "desc": "非制造业PMI同比(%)"},
            },
        },
        "pmi_yearly": {
            "func": ak.macro_china_pmi_yearly,
            "name": "PMI年度",
            "desc": "年度PMI汇总",
        },
        "non_man_pmi": {
            "func": ak.macro_china_non_man_pmi,
            "name": "非制造业PMI",
            "desc": "非制造业采购经理人指数",
        },
        "cx_pmi": {
            "func": ak.macro_china_cx_pmi_yearly,
            "name": "财新PMI年度",
            "desc": "财新制造业PMI年度数据",
        },
        "cx_services_pmi": {
            "func": ak.macro_china_cx_services_pmi_yearly,
            "name": "财新服务业PMI年度",
            "desc": "财新服务业PMI年度数据",
        },
        # -- 货币 / 金融 ----------------------------------------------------
        "money_supply": {
            "func": ak.macro_china_money_supply,
            "name": "货币供应量(M0/M1/M2)",
            "desc": "月度货币供应量，含M0/M1/M2总量及同比环比",
            "columns": {
                "month":       {"name": "月份",                     "desc": "数据月份"},
                "m2_amount":   {"name": "货币和准货币(M2)-数量(亿元)","desc": "M2总量(亿元)"},
                "m2_yoy":      {"name": "货币和准货币(M2)-同比增长",  "desc": "M2同比增长率(%)"},
                "m2_mom":      {"name": "货币和准货币(M2)-环比增长",  "desc": "M2环比增长率(%)"},
                "m1_amount":   {"name": "货币(M1)-数量(亿元)",       "desc": "M1总量(亿元)"},
                "m1_yoy":      {"name": "货币(M1)-同比增长",         "desc": "M1同比增长率(%)"},
                "m1_mom":      {"name": "货币(M1)-环比增长",         "desc": "M1环比增长率(%)"},
                "m0_amount":   {"name": "流通中的现金(M0)-数量(亿元)","desc": "M0总量(亿元)"},
                "m0_yoy":      {"name": "流通中的现金(M0)-同比增长",  "desc": "M0同比增长率(%)"},
                "m0_mom":      {"name": "流通中的现金(M0)-环比增长",  "desc": "M0环比增长率(%)"},
            },
        },
        "m2_yearly": {
            "func": ak.macro_china_m2_yearly,
            "name": "M2年率",
            "desc": "M2年度增长率",
        },
        "lpr": {
            "func": ak.macro_china_lpr,
            "name": "贷款市场报价利率(LPR)",
            "desc": "LPR（1年期/5年期以上）报价历史",
            "columns": {
                "date":     {"name": "日期",     "desc": "报价日期"},
                "lpr_1y":   {"name": "1年期",    "desc": "1年期LPR利率(%)"},
                "lpr_5y":   {"name": "5年期以上","desc": "5年期以上LPR利率(%)"},
            },
        },
        "shibor": {
            "func": ak.macro_china_shibor_all,
            "name": "上海银行间同业拆放利率(Shibor)",
            "desc": "Shibor各期限利率",
        },
        "swap_rate": {
            "func": ak.macro_china_swap_rate,
            "name": "互换利率",
            "desc": "利率互换报价数据",
            "extra": {"start_date": "20231101", "end_date": "20231204"},
        },
        "reserve_requirement_ratio": {
            "func": ak.macro_china_reserve_requirement_ratio,
            "name": "存款准备金率",
            "desc": "央行存款准备金率历次调整记录",
        },
        "central_bank_balance": {
            "func": ak.macro_china_central_bank_balance,
            "name": "央行资产负债表",
            "desc": "人民银行资产负债表",
        },
        "new_financial_credit": {
            "func": ak.macro_china_new_financial_credit,
            "name": "新增信贷数据",
            "desc": "月度新增人民币贷款",
        },
        "bank_financing": {
            "func": ak.macro_china_bank_financing,
            "name": "社会融资规模",
            "desc": "社会融资规模增量月度数据",
        },
        # -- 外汇 / 黄金 ----------------------------------------------------
        "fx_reserves": {
            "func": ak.macro_china_fx_reserves_yearly,
            "name": "外汇储备年度",
            "desc": "年度外汇储备数据",
        },
        "foreign_exchange_gold": {
            "func": ak.macro_china_foreign_exchange_gold,
            "name": "外汇与黄金储备",
            "desc": "外汇储备和黄金储备月度数据",
        },
        "fx_gold": {
            "func": ak.macro_china_fx_gold,
            "name": "黄金储备",
            "desc": "中国黄金储备数据",
        },
        "rmb": {
            "func": ak.macro_china_rmb,
            "name": "人民币汇率中间价",
            "desc": "人民币对主要货币汇率中间价",
        },
        # -- 贸易 -----------------------------------------------------------
        "trade_balance": {
            "func": ak.macro_china_trade_balance,
            "name": "贸易差额",
            "desc": "月度进出口贸易差额",
        },
        "exports_yoy": {
            "func": ak.macro_china_exports_yoy,
            "name": "出口同比",
            "desc": "月度出口同比增长率",
        },
        "imports_yoy": {
            "func": ak.macro_china_imports_yoy,
            "name": "进口同比",
            "desc": "月度进口同比增长率",
        },
        "fdi": {
            "func": ak.macro_china_fdi,
            "name": "外商直接投资(FDI)",
            "desc": "外商直接投资月度数据",
        },
        # -- 消费 -----------------------------------------------------------
        "consumer_goods_retail": {
            "func": ak.macro_china_consumer_goods_retail,
            "name": "社会消费品零售总额",
            "desc": "月度社会消费品零售总额及同比",
        },
        # -- 就业 -----------------------------------------------------------
        "urban_unemployment": {
            "func": ak.macro_china_urban_unemployment,
            "name": "城镇调查失业率",
            "desc": "月度城镇调查失业率",
        },
        # -- 房地产 ---------------------------------------------------------
        "real_estate": {
            "func": ak.macro_china_real_estate,
            "name": "房地产开发投资",
            "desc": "房地产开发投资月度数据",
        },
        "new_house_price": {
            "func": ak.macro_china_new_house_price,
            "name": "新建商品住宅价格指数",
            "desc": "70大中城市新建商品住宅价格指数（默认北京vs上海，可通过extra参数指定城市）",
            "extra": {"city_first": "北京", "city_second": "上海"},
        },
        # -- 财政 -----------------------------------------------------------
        "national_tax_receipts": {
            "func": ak.macro_china_national_tax_receipts,
            "name": "国家税收收入",
            "desc": "国家税收收入分项数据",
        },
        "czsr": {
            "func": ak.macro_china_czsr,
            "name": "财政收入",
            "desc": "全国财政收入月度数据",
        },
        # -- 景气指数 -------------------------------------------------------
        "enterprise_boom_index": {
            "func": ak.macro_china_enterprise_boom_index,
            "name": "企业景气指数",
            "desc": "企业景气指数季度数据",
        },
        # -- 能源 / 物流 ----------------------------------------------------
        "energy_index": {
            "func": ak.macro_china_energy_index,
            "name": "能源指数",
            "desc": "中国能源价格指数",
        },
        "daily_energy": {
            "func": ak.macro_china_daily_energy,
            "name": "能源日评",
            "desc": "每日能源市场评论/数据",
        },
        "freight_index": {
            "func": ak.macro_china_freight_index,
            "name": "货运指数",
            "desc": "中国公路/铁路货运指数",
        },
        "bdti_index": {
            "func": ak.macro_china_bdti_index,
            "name": "波罗的海成品油运输指数",
            "desc": "波罗的海成品油运输指数(Baltic Dirty Tanker Index)",
        },
        "bsi_index": {
            "func": ak.macro_china_bsi_index,
            "name": "波罗的海干散货指数(BSI)",
            "desc": "波罗的海超灵便型船运价指数",
        },
        "lpi_index": {
            "func": ak.macro_china_lpi_index,
            "name": "物流景气指数(LPI)",
            "desc": "中国物流业景气指数月度",
        },
        "agricultural_index": {
            "func": ak.macro_china_agricultural_index,
            "name": "农产品批发价格指数",
            "desc": "农产品批发价格200指数",
        },
        "vegetable_basket": {
            "func": ak.macro_china_vegetable_basket,
            "name": "菜篮子价格指数",
            "desc": "菜篮子产品批发价格指数",
        },
        "commodity_price_index": {
            "func": ak.macro_china_commodity_price_index,
            "name": "大宗商品价格指数",
            "desc": "中国大宗商品价格指数(CCPI)",
        },
        "retail_price_index": {
            "func": ak.macro_china_retail_price_index,
            "name": "商品零售价格指数",
            "desc": "商品零售价格指数月度数据",
        },
        # -- 资本市场 -------------------------------------------------------
        "bond_public": {
            "func": ak.macro_china_bond_public,
            "name": "债券发行量",
            "desc": "债券市场发行量月度数据",
        },
        "stock_market_cap": {
            "func": ak.macro_china_stock_market_cap,
            "name": "股票市值",
            "desc": "A股市场总市值/流通市值",
        },
        "market_margin_sh": {
            "func": ak.macro_china_market_margin_sh,
            "name": "上交所融资融券余额",
            "desc": "上交所融资融券余额日度数据",
        },
        "market_margin_sz": {
            "func": ak.macro_china_market_margin_sz,
            "name": "深交所融资融券余额",
            "desc": "深交所融资融券余额日度数据",
        },
        # -- 其他 -----------------------------------------------------------
        "insurance_income": {
            "func": ak.macro_china_insurance_income,
            "name": "保险业保费收入",
            "desc": "保险业保费收入月度数据",
        },
        "society_electricity": {
            "func": ak.macro_china_society_electricity,
            "name": "全社会用电量",
            "desc": "全社会用电量月度数据",
        },
        "passenger_load_factor": {
            "func": ak.macro_china_passenger_load_factor,
            "name": "民航客座率",
            "desc": "民航客座率月度数据",
        },
        "mobile_number": {
            "func": ak.macro_china_mobile_number,
            "name": "移动电话用户数",
            "desc": "移动电话用户数月度数据",
        },
        "construction_index": {
            "func": ak.macro_china_construction_index,
            "name": "建筑业指数",
            "desc": "建筑业商务活动指数",
        },
    },

    # ======================================================================
    # 美国
    # ======================================================================
    "usa": {
        "cpi_yoy": {
            "func": ak.macro_usa_cpi_yoy,
            "name": "CPI年率",
            "desc": "美国消费者物价指数年率（未季调）",
        },
        "cpi_monthly": {
            "func": ak.macro_usa_cpi_monthly,
            "name": "CPI月率",
            "desc": "美国消费者物价指数月率",
        },
        "core_cpi_monthly": {
            "func": ak.macro_usa_core_cpi_monthly,
            "name": "核心CPI月率",
            "desc": "剔除食品和能源的核心CPI月率",
        },
        "core_pce_price": {
            "func": ak.macro_usa_core_pce_price,
            "name": "核心PCE物价",
            "desc": "核心PCE物价指数（美联储首选的通胀指标）",
        },
        "ppi": {
            "func": ak.macro_usa_ppi,
            "name": "PPI",
            "desc": "美国生产者物价指数",
        },
        "core_ppi": {
            "func": ak.macro_usa_core_ppi,
            "name": "核心PPI",
            "desc": "剔除食品和能源的核心PPI",
        },
        "gdp_monthly": {
            "func": ak.macro_usa_gdp_monthly,
            "name": "GDP月度",
            "desc": "美国GDP月度实际个人消费/投资等",
        },
        "unemployment_rate": {
            "func": ak.macro_usa_unemployment_rate,
            "name": "失业率",
            "desc": "美国月度失业率",
        },
        "non_farm": {
            "func": ak.macro_usa_non_farm,
            "name": "非农就业",
            "desc": "非农就业人口变动",
        },
        "adp_employment": {
            "func": ak.macro_usa_adp_employment,
            "name": "ADP就业人数",
            "desc": "ADP全国就业报告（『小非农』）",
        },
        "initial_jobless": {
            "func": ak.macro_usa_initial_jobless,
            "name": "初请失业金人数",
            "desc": "每周初请失业金人数",
        },
        "trade_balance": {
            "func": ak.macro_usa_trade_balance,
            "name": "贸易差额",
            "desc": "美国国际贸易差额月度",
        },
        "retail_sales": {
            "func": ak.macro_usa_retail_sales,
            "name": "零售销售",
            "desc": "美国零售销售月度数据",
        },
        "industrial_production": {
            "func": ak.macro_usa_industrial_production,
            "name": "工业产出",
            "desc": "美国工业产出月度",
        },
        "ism_pmi": {
            "func": ak.macro_usa_ism_pmi,
            "name": "ISM制造业PMI",
            "desc": "ISM制造业采购经理人指数",
        },
        "ism_non_pmi": {
            "func": ak.macro_usa_ism_non_pmi,
            "name": "ISM非制造业PMI",
            "desc": "ISM非制造业采购经理人指数",
        },
        "cb_consumer_confidence": {
            "func": ak.macro_usa_cb_consumer_confidence,
            "name": "CB消费者信心",
            "desc": "美国咨商会消费者信心指数",
        },
        "michigan_consumer_sentiment": {
            "func": ak.macro_usa_michigan_consumer_sentiment,
            "name": "密歇根消费者信心",
            "desc": "密歇根大学消费者信心指数",
        },
        "existing_home_sales": {
            "func": ak.macro_usa_exist_home_sales,
            "name": "成屋销售",
            "desc": "美国成屋销售年化总数",
        },
        "new_home_sales": {
            "func": ak.macro_usa_new_home_sales,
            "name": "新屋销售",
            "desc": "美国新屋销售年化总数",
        },
        "house_price_index": {
            "func": ak.macro_usa_house_price_index,
            "name": "房价指数",
            "desc": "美国FHFA房价指数",
        },
        "api_crude_stock": {
            "func": ak.macro_usa_api_crude_stock,
            "name": "API原油库存",
            "desc": "美国石油协会原油库存周度",
        },
        "eia_crude_rate": {
            "func": ak.macro_usa_eia_crude_rate,
            "name": "EIA原油库存",
            "desc": "美国能源信息署原油库存周度",
        },
    },

    # ======================================================================
    # 欧元区
    # ======================================================================
    "euro": {
        "cpi_yoy":                 {"func": ak.macro_euro_cpi_yoy,                 "name": "CPI年率", "desc": "欧元区调和CPI年率"},
        "cpi_mom":                 {"func": ak.macro_euro_cpi_mom,                 "name": "CPI月率", "desc": "欧元区调和CPI月率"},
        "gdp_yoy":                 {"func": ak.macro_euro_gdp_yoy,                 "name": "GDP年率", "desc": "欧元区GDP年率"},
        "manufacturing_pmi":       {"func": ak.macro_euro_manufacturing_pmi,       "name": "制造业PMI", "desc": "欧元区制造业PMI"},
        "services_pmi":            {"func": ak.macro_euro_services_pmi,            "name": "服务业PMI", "desc": "欧元区服务业PMI"},
        "unemployment_rate_mom":   {"func": ak.macro_euro_unemployment_rate_mom,   "name": "失业率月率", "desc": "欧元区失业率月率"},
        "trade_balance":           {"func": ak.macro_euro_trade_balance,           "name": "贸易差额", "desc": "欧元区贸易帐（未季调）"},
        "retail_sales_mom":        {"func": ak.macro_euro_retail_sales_mom,        "name": "零售销售月率", "desc": "欧元区零售销售月率"},
        "industrial_production_mom":{"func": ak.macro_euro_industrial_production_mom,"name": "工业产出月率", "desc": "欧元区工业产出月率"},
    },

    # ======================================================================
    # 英国
    # ======================================================================
    "uk": {
        "cpi_yearly":         {"func": ak.macro_uk_cpi_yearly,         "name": "CPI年率",   "desc": "英国CPI年率"},
        "gdp_yearly":         {"func": ak.macro_uk_gdp_yearly,         "name": "GDP年率",   "desc": "英国GDP年率"},
        "gdp_quarterly":      {"func": ak.macro_uk_gdp_quarterly,      "name": "GDP季率",   "desc": "英国GDP季率"},
        "unemployment_rate":  {"func": ak.macro_uk_unemployment_rate,  "name": "失业率",    "desc": "英国失业率"},
        "trade":              {"func": ak.macro_uk_trade,              "name": "贸易帐",    "desc": "英国贸易帐"},
        "retail_monthly":     {"func": ak.macro_uk_retail_monthly,     "name": "零售销售月率","desc": "英国零售销售月率"},
        "bank_rate":          {"func": ak.macro_uk_bank_rate,          "name": "央行利率",  "desc": "英国央行利率决议"},
    },

    # ======================================================================
    # 日本
    # ======================================================================
    "japan": {
        "cpi_yearly":           {"func": ak.macro_japan_cpi_yearly,           "name": "CPI年率",       "desc": "日本CPI年率"},
        "core_cpi_yearly":      {"func": ak.macro_japan_core_cpi_yearly,      "name": "核心CPI年率",    "desc": "日本核心CPI年率"},
        "unemployment_rate":    {"func": ak.macro_japan_unemployment_rate,    "name": "失业率",         "desc": "日本失业率"},
        "bank_rate":            {"func": ak.macro_japan_bank_rate,            "name": "央行利率",       "desc": "日本央行利率决议"},
    },

    # ======================================================================
    # 德国
    # ======================================================================
    "germany": {
        "cpi_yearly": {"func": ak.macro_germany_cpi_yearly, "name": "CPI年率", "desc": "德国CPI年率"},
        "gdp":        {"func": ak.macro_germany_gdp,        "name": "GDP",     "desc": "德国GDP数据"},
    },

    # ======================================================================
    # 加拿大
    # ======================================================================
    "canada": {
        "cpi_yearly":          {"func": ak.macro_canada_cpi_yearly,          "name": "CPI年率",   "desc": "加拿大CPI年率"},
        "gdp_monthly":         {"func": ak.macro_canada_gdp_monthly,         "name": "GDP月度",   "desc": "加拿大GDP月度"},
        "unemployment_rate":   {"func": ak.macro_canada_unemployment_rate,   "name": "失业率",    "desc": "加拿大失业率"},
        "trade":               {"func": ak.macro_canada_trade,               "name": "贸易帐",    "desc": "加拿大贸易帐"},
    },

    # ======================================================================
    # 澳大利亚
    # ======================================================================
    "australia": {
        "cpi_yearly":          {"func": ak.macro_australia_cpi_yearly,        "name": "CPI年率",   "desc": "澳大利亚CPI年率"},
        "unemployment_rate":   {"func": ak.macro_australia_unemployment_rate, "name": "失业率",    "desc": "澳大利亚失业率"},
        "trade":               {"func": ak.macro_australia_trade,             "name": "贸易帐",    "desc": "澳大利亚贸易帐"},
    },
}


# ---------------------------------------------------------------------------
# API 类
# ---------------------------------------------------------------------------

class AkshareMacro:
    """宏观数据 API — 按国家分发到对应的 akshare 函数"""

    def __init__(self):
        pass

    # -- 查询 ---------------------------------------------------------------

    def get_supported_countries(self) -> List[Dict[str, Any]]:
        """返回所有支持的国家/地区列表"""
        return [
            {
                "country": code,
                "indicator_count": len(indicators),
            }
            for code, indicators in _REGISTRY.items()
        ]

    def get_indicator_list(self, country: Optional[str] = None) -> Dict[str, Any]:
        """返回指定国家（或全部）的指标列表

        Parameters
        ----------
        country : str, optional
            国家代码。为 None 时返回全部国家。
        """
        def _describe_entry(key: str, entry: _IndicatorEntry) -> dict:
            cols = entry.get("columns")
            column_count = len(cols) if cols else None
            return {
                "indicator":    key,
                "name":         entry["name"],
                "desc":         entry.get("desc", ""),
                "column_count": column_count,
                "extra_params": list(entry.get("extra", {}).keys()) if entry.get("extra") else [],
            }

        if country is not None:
            country = country.lower()
            if country not in _REGISTRY:
                return {}
            return {
                country: [_describe_entry(k, v) for k, v in _REGISTRY[country].items()]
            }

        result = {}
        for code, indicators in _REGISTRY.items():
            result[code] = [_describe_entry(k, v) for k, v in indicators.items()]
        return result

    def get_indicator_schema(self, country: str, indicator: str) -> Optional[Dict[str, Any]]:
        """获取指定指标的完整 schema（含输出列定义）

        返回结构:
            {
                "country":   "china",
                "indicator": "cpi",
                "name":      "居民消费价格指数(CPI)",
                "desc":      "...",
                "extra_params": [...],
                "columns": {
                    "month": {"name": "月份", "desc": "数据所属月份"},
                    ...
                }
            }
        如果 registry 中没有显式 columns，尝试用空参数调用函数自动推导列名。
        """
        country = country.lower()
        indicator = indicator.lower()

        country_registry = _REGISTRY.get(country)
        if country_registry is None:
            return None

        entry = country_registry.get(indicator)
        if entry is None:
            return None

        schema: Dict[str, Any] = {
            "country":      country,
            "indicator":    indicator,
            "name":         entry["name"],
            "desc":         entry.get("desc", ""),
            "extra_params": list(entry.get("extra", {}).keys()) if entry.get("extra") else [],
            "columns":      {},
        }

        # 优先用注册表中的 columns 定义
        if entry.get("columns"):
            schema["columns"] = entry["columns"]
            return schema

        # 否则：自动推导
        try:
            func: Callable = entry["func"]
            df = func()
            if df is not None and not df.empty:
                for col in df.columns:
                    schema["columns"][col] = {"name": col, "desc": ""}
        except Exception:
            logger.debug("AkshareMacro: could not auto-derive columns for %s/%s", country, indicator)

        return schema

    def get_macro_data(self, country: str, indicator: str, **kwargs) -> Optional[pd.DataFrame]:
        """获取指定国家 + 指标的宏观数据

        Parameters
        ----------
        country : str
            国家代码，如 "china"、"usa"
        indicator : str
            指标 key，如 "cpi"、"gdp"、"pmi"
        **kwargs : dict
            传递给底层 akshare 函数的额外参数，
            例如 new_house_price 支持 city_first / city_second
        """
        country = country.lower()
        indicator = indicator.lower()

        country_registry = _REGISTRY.get(country)
        if country_registry is None:
            logger.warning("AkshareMacro: unsupported country '%s'", country)
            return None

        entry = country_registry.get(indicator)
        if entry is None:
            logger.warning("AkshareMacro: unsupported indicator '%s' for country '%s'",
                           indicator, country)
            return None

        try:
            func: Callable = entry["func"]
            extra_defaults = entry.get("extra", {})
            call_kwargs = {**extra_defaults, **kwargs}
            df = func(**call_kwargs)
            if df is None or df.empty:
                return None
            return df
        except Exception as e:
            logger.error("AkshareMacro: %s/%s failed — %s", country, indicator, e)
            return None
