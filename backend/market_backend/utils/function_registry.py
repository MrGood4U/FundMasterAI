"""
Market-backend 全部接口的 Function Calling 定义。

每个函数包含 LLM agent 所需的 name / description / parameters / returns，
以及路由元信息（path / method），agent 可据此生成 HTTP 请求并解析响应。

所有接口的 HTTP 响应格式统一为:
  {"code": 200, "data": [...], "message": "success"}
  data 为对象数组，每条记录的结构见各函数的 returns 字段。
"""

FUNCTIONS = [
    # =====================================================================
    # A 股
    # =====================================================================
    {
        "name": "get_stock_spot",
        "description": "获取单只A股实时行情，可按股票代码或名称查询。",
        "path": "/api/market/stock/a/one_spot",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "description": "数据源平台",
                    "enum": ["eastmoney", "sina"],
                },
                "code": {
                    "type": "string",
                    "description": "股票代码，如 600519。与 name 二选一",
                },
                "name": {
                    "type": "string",
                    "description": "股票名称，如 贵州茅台。与 code 二选一",
                },
            },
            "required": ["platform"],
        },
        "returns": {
            "sequence": "序号",
            "stock_code": "股票代码",
            "stock_name": "股票名称",
            "latest_price": "最新价",
            "open": "开盘价",
            "high": "最高价",
            "low": "最低价",
            "volume": "成交量",
            "turnover": "成交额",
            "change_pct": "涨跌幅(%)",
            "change_amount": "涨跌额",
            "prev_close": "昨收价",
            "amplitude": "振幅(%)",
            "volume_ratio": "量比",
            "turnover_rate": "换手率(%)",
            "pe_dynamic": "市盈率(动态)",
            "pb": "市净率",
            "total_market_cap": "总市值",
            "circulating_market_cap": "流通市值",
            "rise_speed": "涨速",
            "change_5min": "5分钟涨跌幅(%)",
            "change_60d": "60日涨跌幅(%)",
            "change_ytd": "年初至今涨跌幅(%)",
        },
    },
    {
        "name": "get_all_stock_spot",
        "description": "获取A股全部股票实时行情列表。数据量较大，适合批量筛选，不要逐条遍历全量数据。",
        "path": "/api/market/stock/a/all_spot",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "description": "数据源平台",
                    "enum": ["eastmoney", "sina"],
                },
            },
            "required": ["platform"],
        },
        "returns": {
            "sequence": "序号",
            "stock_code": "股票代码",
            "stock_name": "股票名称",
            "latest_price": "最新价",
            "open": "开盘价",
            "high": "最高价",
            "low": "最低价",
            "volume": "成交量(手)",
            "turnover": "成交额(元)",
            "change_pct": "涨跌幅(%)",
            "change_amount": "涨跌额(元)",
            "prev_close": "昨收价",
            "amplitude": "振幅(%)",
            "volume_ratio": "量比",
            "turnover_rate": "换手率(%)",
            "pe_dynamic": "市盈率(动态)",
            "pb": "市净率",
            "total_market_cap": "总市值",
            "circulating_market_cap": "流通市值",
            "rise_speed": "涨速",
            "change_5min": "5分钟涨跌幅(%)",
            "change_60d": "60日涨跌幅(%)",
            "change_ytd": "年初至今涨跌幅(%)",
        },
    },
    {
        "name": "get_stock_hist",
        "description": "获取A股历史日线/周线/月线行情（OHLCV）。适合查看K线走势、计算涨跌幅等。",
        "path": "/api/market/stock/a/hist",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "description": "数据源平台，eastmoney 或 sina, 推荐eastmoney",
                    "enum": ["eastmoney", "sina"],
                },
                "code": {
                    "type": "string",
                    "description": "股票代码，如 600519",
                },
                "period": {
                    "type": "string",
                    "description": "K线周期",
                    "enum": ["daily", "weekly", "monthly"],
                },
                "start_date": {
                    "type": "string",
                    "description": "起始日期，格式 YYYYMMDD，如 20250101",
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期，格式 YYYYMMDD，如 20250528",
                },
                "adjust": {
                    "type": "string",
                    "description": "复权方式。qfq=前复权，hfq=后复权，空字符串=不复权",
                    "enum": ["", "qfq", "hfq"],
                },
            },
            "required": ["platform", "code"],
        },
        "returns": {
            "date": "交易日期",
            "stock_code": "股票代码",
            "stock_name": "股票名称",
            "open": "开盘价",
            "close": "收盘价",
            "high": "最高价",
            "low": "最低价",
            "volume": "成交量(手)",
            "turnover": "成交额(元)",
            "amplitude": "振幅(%)",
            "change_pct": "涨跌幅(%)",
            "change_amount": "涨跌额(元)",
            "turnover_rate": "换手率(%)",
        },
    },
    {
        "name": "get_stock_hist_kline",
        "description": "获取A股历史行情并附带全部技术指标。包含 MA5/10/20/60、MACD(DIF/DEA/柱)、RSI(14)、KDJ(K/D/J)、BOLL(上/中/下轨)。适合技术分析选股。返回字段多，分析前先确认关注的指标。",
        "path": "/api/market/stock/a/hist_kline",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "description": "数据源平台",
                    "enum": ["eastmoney", "sina"],
                },
                "code": {
                    "type": "string",
                    "description": "股票代码",
                },
                "period": {
                    "type": "string",
                    "description": "K线周期",
                    "enum": ["daily", "weekly", "monthly"],
                },
                "start_date": {
                    "type": "string",
                    "description": "起始日期，格式 YYYYMMDD",
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期，格式 YYYYMMDD",
                },
                "adjust": {
                    "type": "string",
                    "description": "复权方式",
                    "enum": ["", "qfq", "hfq"],
                },
            },
            "required": ["platform", "code"],
        },
        "returns": {
            "date": "交易日期",
            "stock_code": "股票代码",
            "stock_name": "股票名称",
            "open": "开盘价",
            "close": "收盘价",
            "high": "最高价",
            "low": "最低价",
            "volume": "成交量(手)",
            "change_pct": "涨跌幅(%)",
            "turnover_rate": "换手率(%)",
            "ma5": "5日均线",
            "ma10": "10日均线",
            "ma20": "20日均线",
            "ma60": "60日均线",
            "macd_dif": "MACD快线(DIF)",
            "macd_dea": "MACD慢线(DEA)",
            "macd_bar": "MACD柱状值(2*(DIF-DEA))",
            "rsi": "RSI(14)相对强弱指标",
            "kdj_k": "KDJ-K值",
            "kdj_d": "KDJ-D值",
            "kdj_j": "KDJ-J值",
            "boll_upper": "BOLL上轨",
            "boll_mid": "BOLL中轨(20日均线)",
            "boll_lower": "BOLL下轨",
        },
    },
    {
        "name": "get_stock_bid_ask",
        "description": "获取A股盘口数据，包含买卖盘口、委比、量比、涨停跌停价、内外盘等。",
        "path": "/api/market/stock/a/bid_ask",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "description": "数据源平台",
                },
                "code": {
                    "type": "string",
                    "description": "股票代码",
                },
            },
            "required": ["code"],
        },
        "returns": {
            "sell_5": "卖五价",
            "sell_5_vol": "卖五量(手)",
            "sell_4": "卖四价",
            "sell_4_vol": "卖四量(手)",
            "sell_3": "卖三价",
            "sell_3_vol": "卖三量(手)",
            "sell_2": "卖二价",
            "sell_2_vol": "卖二量(手)",
            "sell_1": "卖一价",
            "sell_1_vol": "卖一量(手)",
            "buy_1": "买一价",
            "buy_1_vol": "买一量(手)",
            "buy_2": "买二价",
            "buy_2_vol": "买二量(手)",
            "buy_3": "买三价",
            "buy_3_vol": "买三量(手)",
            "buy_4": "买四价",
            "buy_4_vol": "买四量(手)",
            "buy_5": "买五价",
            "buy_5_vol": "买五量(手)",
            "latest_price": "最新价",
            "average_price": "均价",
            "change_pct": "涨跌幅(%)",
            "change_amount": "涨跌额",
            "total_volume": "总手",
            "turnover": "成交额",
            "turnover_rate": "换手率(%)",
            "volume_ratio": "量比",
            "high": "最高价",
            "low": "最低价",
            "open": "今开价",
            "prev_close": "昨收价",
            "upper_limit": "涨停价",
            "lower_limit": "跌停价",
            "bid_volume": "外盘",
            "ask_volume": "内盘",
        },
    },
    {
        "name": "get_stock_batch_spot",
        "description": "批量获取多只A股实时行情。一次传入多个代码，从全量行情中过滤返回匹配的股票，比逐个调用 get_stock_spot 效率高得多。",
        "path": "/api/market/stock/a/batch_spot",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "description": "数据源平台，默认 eastmoney",
                },
                "codes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "股票代码列表，如 ['600519', '000858', '300750']",
                },
            },
            "required": ["codes"],
        },
        "returns": {
            "stock_code": "股票代码",
            "stock_name": "股票名称",
            "latest_price": "最新价",
            "change_pct": "涨跌幅(%)",
            "volume": "成交量",
            "turnover": "成交额",
            "pe_dynamic": "市盈率(动态)",
            "pb": "市净率",
            "total_market_cap": "总市值",
        },
    },
    {
        "name": "get_stock_flow",
        "description": "获取个股大额资金流向。返回主力/超大单/大单/中单/小单的净流入和净占比，适合分析主力资金动向和建仓/出货行为。",
        "path": "/api/market/stock/flow",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "stock_code": {
                    "type": "string",
                    "description": "股票代码，如 600519, 000001.SZ",
                },
            },
            "required": ["stock_code"],
        },
        "returns": {
            "fs_code": "股票代码",
            "trade_date": "交易日期",
            "net_inflow_main": "主力净流入(元)",
            "net_inflow_super": "超大单净流入(元)",
            "net_inflow_large": "大单净流入(元)",
            "net_inflow_medium": "中单净流入(元)",
            "net_inflow_small": "小单净流入(元)",
            "net_inflow_main_ratio": "主力净流入占比(%)",
            "net_inflow_super_ratio": "超大单净流入占比(%)",
            "net_inflow_large_ratio": "大单净流入占比(%)",
            "net_inflow_medium_ratio": "中单净流入占比(%)",
            "net_inflow_small_ratio": "小单净流入占比(%)",
        },
    },
    {
        "name": "get_stock_flow_industry",
        "description": "获取全市场行业资金流向。返回各行业的主力净流入和净流入占比排名，适合判断当前资金偏好哪个行业板块。无参数，GET请求。",
        "path": "/api/market/stock/flow_industry",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "returns": {
            "industry": "行业名称",
            "net_inflow": "主力净流入(元)",
            "net_inflow_ratio": "主力净流入占比(%)",
            "change_rate": "涨跌幅(%)",
        },
    },
    {
        "name": "get_stock_lhb",
        "description": "获取龙虎榜数据（上榜股票列表）。展示每日涨跌幅偏离值达7%、换手率达20%、连续三个交易日涨幅偏离值累计达20%等异动上榜的股票，包含买入/卖出金额前五席位、净买额、机构席位明细。适合追踪游资和机构动向。日期格式YYYYMMDD。",
        "path": "/api/market/stock/lhb",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "起始日期，格式 YYYYMMDD，如 20250601",
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期，格式 YYYYMMDD，如 20250630",
                },
            },
            "required": ["start_date", "end_date"],
        },
        "returns": {
            "buy_amount": "买入金额(元)",
            "change_rate": "涨跌幅(%)",
            "close_price": "收盘价",
            "fs_code": "股票代码",
            "net_buy_amount": "净买额(元)",
            "reason": "上榜原因",
            "sell_amount": "卖出金额(元)",
            "trade_date": "交易日期",
            "turnover_rate": "换手率(%)"
        },
    },
    {
        "name": "get_stock_lhb_detail",
        "description": "获取单只股票在指定交易日的龙虎榜席位明细。展示该股当天所有席位的买入/卖出金额、净买额和机构参与情况。用于深入分析某只异动股的席位结构和主力意图。",
        "path": "/api/market/stock/lhb_detail",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "stock_code": {
                    "type": "string",
                    "description": "股票代码，如 600519",
                },
                "trade_date": {
                    "type": "string",
                    "description": "交易日期，格式 YYYYMMDD，如 20250630",
                },
            },
            "required": ["stock_code", "trade_date"],
        },
        "returns": {
            "fs_code": "股票代码",
            "trade_date": "交易日期",
            "broker_name": "席位名称",
            "buy_amount": "买入金额(元)",
            "sell_amount": "卖出金额(元)",
            "net_amount": "净买额(元)",
        },
    },

    # =====================================================================
    # 公募基金
    # =====================================================================
    {
        "name": "get_fund_spot",
        "description": "获取单只基金实时行情，可按基金代码或名称查询。返回最新价、IOPV、折价率、资金流向等。",
        "path": "/api/market/fund_public/real_time_get_one",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "description": "数据源平台, 优先使用tonghuashun更稳定",
                    "enum": ["tonghuashun", "eastmoney", "sina"],
                },
                "symbol": {
                    "type": "string",
                    "description": "基金类型，如 股票型, 债券型, 混合型, ETF, LOF, QDII, 保本型, 指数型, 全部",
                    "enum": ["stock", "bond", "mixed", "ETF", "LOF", "QDII", "guaranteed", "index", "all"],
                },
                "code": {
                    "type": "string",
                    "description": "基金代码。与 name 二选一",
                },
                "name": {
                    "type": "string",
                    "description": "基金名称。与 code 二选一",
                },
            },
            "required": ["platform", "symbol"],
        },
        "returns": {
            "fund_code": "基金代码",
            "fund_name": "基金名称",
            "fund_type": "基金类型",
            "current_accumulated_net_value": "当前累计净值",
            "current_unit_net_value": "当前单位净值",
            "growth_rate": "增长率(%)",
            "growth_value": "增长值",
            "latest_accumulated_net_value": "最新累计净值",
            "latest_trading_date": "最新交易日",
            "latest_unit_net_value": "最新单位净值",
            "prev_accumulated_net_value": "前一日累计净值",
            "prev_unit_net_value": "前一日单位净值",
            "query_date": "查询日期",
            "redemption_status": "赎回状态",
            "sequence": "序号",
            "subscription_status": "申购状态",
        },
    },
    {
        "name": "get_all_fund_spot",
        "description": "获取指定类型下全部基金的实时行情列表。适合筛选和排行场景。",
        "path": "/api/market/fund_public/real_time_get_all",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "description": "数据源平台, 优先使用tonghuashun更稳定",
                    "enum": ["tonghuashun", "eastmoney", "sina"],
                },
                "symbol": {
                    "type": "string",
                    "description": "基金类型，如 股票型, 债券型, 混合型, ETF, LOF, QDII, 保本型, 指数型, 全部",
                    "enum": ["stock", "bond", "mixed", "ETF", "LOF", "QDII", "guaranteed", "index", "all"],
                },
            },
            "required": ["platform", "symbol"],
        },
        "returns": {
            "fund_code": "基金代码",
            "fund_name": "基金名称",
            "fund_type": "基金类型",
            "current_accumulated_net_value": "当前累计净值",
            "current_unit_net_value": "当前单位净值",
            "growth_rate": "增长率(%)",
            "growth_value": "增长值",
            "latest_accumulated_net_value": "最新累计净值",
            "latest_trading_date": "最新交易日",
            "latest_unit_net_value": "最新单位净值",
            "prev_accumulated_net_value": "前一日累计净值",
            "prev_unit_net_value": "前一日单位净值",
            "query_date": "查询日期",
            "redemption_status": "赎回状态",
            "sequence": "序号",
            "subscription_status": "申购状态",
        },
    },
    {
        "name": "get_fund_batch_spot",
        "description": "批量获取多只基金实时行情。从全量行情中按代码集合过滤，比逐个调用 get_fund_spot 更高效。",
        "path": "/api/market/fund_public/batch_spot",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "description": "数据源平台, 优先使用tonghuashun更稳定",
                    "enum": ["tonghuashun", "eastmoney", "sina"],
                },
                "symbol": {
                    "type": "string",
                    "description": "基金类型，如 股票型, 债券型, 混合型, ETF, LOF, QDII, 保本型, 指数型, 全部",
                    "enum": ["stock", "bond", "mixed", "ETF", "LOF", "QDII", "guaranteed", "index", "all"],
                },
                "codes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "基金代码列表，如 ['510050', '159915']",
                },
            },
            "required": ["platform", "symbol", "codes"],
        },
        "returns": {
            "fund_code": "基金代码",
            "fund_name": "基金名称",
            "fund_type": "基金类型",
            "current_accumulated_net_value": "当前累计净值",
            "current_unit_net_value": "当前单位净值",
            "growth_rate": "增长率(%)",
            "growth_value": "增长值",
            "latest_accumulated_net_value": "最新累计净值",
            "latest_trading_date": "最新交易日",
            "latest_unit_net_value": "最新单位净值",
            "prev_accumulated_net_value": "前一日累计净值",
            "prev_unit_net_value": "前一日单位净值",
            "query_date": "查询日期",
            "redemption_status": "赎回状态",
            "sequence": "序号",
            "subscription_status": "申购状态",
        },
    },
    {
        "name": "get_fund_hist",
        "description": "获取公募基金历史净值数据（单位净值、累计净值、日涨跌幅）。数据源为 efinance，覆盖全部开放式基金。无需指定 platform/period，仅需基金代码即可获取全部历史净值。支持 start_date/end_date 过滤日期范围。",
        "path": "/api/market/fund_public/hist",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "基金代码，如 000001（华夏成长混合）",
                },
                "start_date": {
                    "type": "string",
                    "description": "起始日期，格式 YYYYMMDD。不传则返回全部历史",
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期，格式 YYYYMMDD。不传则返回全部历史",
                },
                "platform": {
                    "type": "string",
                    "description": "保留字段，efinance 不依赖此参数",
                },
                "symbol": {
                    "type": "string",
                    "description": "保留字段",
                },
                "period": {
                    "type": "string",
                    "description": "保留字段，efinance 只返回日级别数据",
                },
                "adjust": {
                    "type": "string",
                    "description": "保留字段",
                },
            },
            "required": ["platform", "symbol", "code"],
        },
        "returns": {
            "date": "净值日期",
            "unit_net_value": "单位净值（实际买入卖出价格，技术分析推荐使用此列）",
            "accumulated_net_value": "累计净值（含历史分红拆分，不建议用于技术分析）",
            "change_pct": "日涨跌幅(%)",
        },
    },
    {
        "name": "get_fund_hist_kline",
        "description": "获取公募基金历史净值并附带全部技术指标。与 get_fund_hist 数据源相同（efinance），额外用单位净值(unit_net_value)计算 MA5/10/20/60、MACD、RSI、KDJ、BOLL。注意：基金无日内 OHLC，KDJ/BOLL 以净值替代 high/low，信号强度弱于股票，使用时需结合其他信息综合判断。",
        "path": "/api/market/fund_public/hist_kline",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "基金代码",
                },
                "start_date": {
                    "type": "string",
                    "description": "起始日期，格式 YYYYMMDD",
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期，格式 YYYYMMDD",
                },
                "platform": {
                    "type": "string",
                    "description": "保留字段",
                },
                "symbol": {
                    "type": "string",
                    "description": "保留字段",
                },
                "period": {
                    "type": "string",
                    "description": "保留字段",
                },
                "adjust": {
                    "type": "string",
                    "description": "保留字段",
                },
            },
            "required": ["platform", "symbol", "code"],
        },
        "returns": {
            "date": "净值日期",
            "unit_net_value": "单位净值（分析主列，所有指标以此计算）",
            "accumulated_net_value": "累计净值",
            "change_pct": "日涨跌幅(%)",
            "ma5": "5日均线(净值)",
            "ma10": "10日均线(净值)",
            "ma20": "20日均线(净值)",
            "ma60": "60日均线(净值)",
            "macd_dif": "MACD快线(DIF)",
            "macd_dea": "MACD慢线(DEA)",
            "macd_bar": "MACD柱状值",
            "rsi": "RSI(14)相对强弱指标",
            "kdj_k": "KDJ-K值",
            "kdj_d": "KDJ-D值",
            "kdj_j": "KDJ-J值",
            "boll_upper": "BOLL上轨",
            "boll_mid": "BOLL中轨",
            "boll_lower": "BOLL下轨",
        },
    },
    {
        "name": "get_fund_hist_min",
        "description": "(eastmoney数据源不稳定，不建议使用此接口)获取ETF/LOF基金分钟级K线数据。仅 eastmoney 数据源，支持 1/5/15/30/60 分钟周期。适合交易时点分析和短期择时。",
        "path": "/api/market/fund_public/hist_min",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "description": "数据源平台，目前仅支持 eastmoney",
                    "enum": ["eastmoney"],
                },
                "symbol": {
                    "type": "string",
                    "description": "基金类型",
                    "enum": ["ETF", "LOF"],
                },
                "code": {
                    "type": "string",
                    "description": "基金代码",
                },
                "period": {
                    "type": "string",
                    "description": "分钟周期",
                    "enum": ["1", "5", "15", "30", "60"],
                },
                "start_date": {
                    "type": "string",
                    "description": "起始日期，格式 YYYYMMDD 或 YYYY-MM-DD",
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期",
                },
                "adjust": {
                    "type": "string",
                    "description": "复权方式",
                    "enum": ["", "qfq", "hfq"],
                },
            },
            "required": ["platform", "code"],
        },
        "returns": {
            "time": "K线时间",
            "open": "开盘价",
            "close": "收盘价",
            "high": "最高价",
            "low": "最低价",
            "volume": "成交量",
            "turnover": "成交额",
            "amplitude": "振幅(%)",
            "change_pct": "涨跌幅(%)",
            "change_amount": "涨跌额",
            "turnover_rate": "换手率(%)",
        },
    },
    {
        "name": "get_fund_hist_min_kline",
        "description": "(eastmoney数据源不稳定，不建议使用此接口)获取ETF/LOF基金分钟级K线并附带全部技术指标（MA/MACD/RSI/KDJ/BOLL）。适用于ETF短线交易的技术分析，数据含 OHLC，因此 KDJ/BOLL 指标比日净值版的更可靠。",
        "path": "/api/market/fund_public/hist_min_kline",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "description": "数据源平台，仅 eastmoney",
                    "enum": ["eastmoney"],
                },
                "symbol": {
                    "type": "string",
                    "description": "基金类型",
                    "enum": ["ETF", "LOF"],
                },
                "code": {
                    "type": "string",
                    "description": "基金代码",
                },
                "period": {
                    "type": "string",
                    "description": "分钟周期",
                    "enum": ["1", "5", "15", "30", "60"],
                },
                "start_date": {
                    "type": "string",
                    "description": "起始日期",
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期",
                },
                "adjust": {
                    "type": "string",
                    "description": "复权方式",
                    "enum": ["", "qfq", "hfq"],
                },
            },
            "required": ["platform", "code"],
        },
        "returns": {
            "time": "K线时间",
            "open": "开盘价",
            "close": "收盘价",
            "high": "最高价",
            "low": "最低价",
            "volume": "成交量",
            "turnover": "成交额",
            "change_pct": "涨跌幅(%)",
            "turnover_rate": "换手率(%)",
            "ma5": "5周期均线",
            "ma10": "10周期均线",
            "ma20": "20周期均线",
            "ma60": "60周期均线",
            "macd_dif": "MACD快线",
            "macd_dea": "MACD慢线",
            "macd_bar": "MACD柱",
            "rsi": "RSI(14)",
            "kdj_k": "KDJ-K",
            "kdj_d": "KDJ-D",
            "kdj_j": "KDJ-J",
            "boll_upper": "BOLL上轨",
            "boll_mid": "BOLL中轨",
            "boll_lower": "BOLL下轨",
        },
    },
    {
        "name": "get_fund_name_list",
        "description": "获取全市场公募基金名称列表。用于搜索基金、通过名称查找代码。无参数，GET 请求。",
        "path": "/api/market/fund_public/fund_name_list",
        "method": "GET",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "returns": {
            "fund_code": "基金代码",
            "fund_name": "基金简称",
            "fund_type": "基金类型",
            "pinyin_abbr": "拼音缩写（可用于搜索）",
            "pinyin_full": "拼音全称",
        },
    },
    {
        "name": "get_fund_portfolio_holds",
        "description": "获取指定基金的持仓股票明细。显示基金买了哪些股票、仓位比例、持股市值。用于分析基金的投资风格和重仓方向。",
        "path": "/api/market/fund_public/portfolio_holds",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "基金代码",
                },
                "year": {
                    "type": "string",
                    "description": "年份，如 2025，默认为当前年份",
                },
            },
            "required": ["code"],
        },
        "returns": {
            "sequence": "序号",
            "stock_code": "股票代码",
            "stock_name": "股票名称",
            "net_value_pct": "占净值比例(%)",
            "hold_shares": "持股数量",
            "hold_market_value": "持仓市值",
            "quarter": "所属季度",
        },
    },
    {
        "name": "get_fund_individual_analysis",
        "description": "获取基金的风险收益分析指标。包含年化波动率、夏普比率、最大回撤、与同类基金的风险收益对比。用于评估基金的风险调整后收益，是选基的核心参考。",
        "path": "/api/market/fund_public/individual_analysis",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "基金代码",
                },
            },
            "required": ["code"],
        },
        "returns": {
            "period": "评估周期（如 近1年、近3年）",
            "annualized_volatility": "年化波动率(%)，越低越稳定",
            "annualized_sharpe_ratio": "年化夏普比率，越高性价比越好",
            "max_drawdown": "最大回撤(%)，越小抗跌能力越强",
            "risk_return_ratio_vs_peers": "较同类风险收益比",
            "risk_robustness_vs_peers": "较同类抗风险波动",
        },
    },
    {
        "name": "get_fund_profit_probability",
        "description": "获取基金不同持有时长下的历史盈利概率和平均收益。用于评估买入后持有多久大概率为正收益，帮助制定持有策略。",
        "path": "/api/market/fund_public/profit_probability",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "基金代码",
                },
            },
            "required": ["code"],
        },
        "returns": {
            "holding_period": "持有时长",
            "profit_probability": "盈利概率(%)",
            "average_return": "平均收益率(%)",
        },
    },
    {
        "name": "get_fund_value_estimation",
        "description": "获取指定基金的盘中实时净值估算。包含估算值、估算增长率、已公布的上一交易日净值、估算偏差。帮助在交易时段判断基金当日大致涨跌。这是盘中估算，非实际净值。",
        "path": "/api/market/fund_public/value_estimation",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "基金代码",
                },
                "fund_type": {
                    "type": "string",
                    "description": "基金类型，默认 all, 包含股票型, 混合型, 债券型, 指数型, QDII, ETF联接, LOF, 场内交易基金",
                    "enum": ["all", "stock", "mixed", "bond", "index", "qdii", "etf_link", "lof", "exchange_traded_fund"],
                },
            },
            "required": ["code"],
        },
        "returns": {
            "fund_code": "基金代码",
            "fund_name": "基金名称",
            "estimation_value": "盘中估算净值",
            "estimation_growth_rate": "估算增长率(%)",
            "reported_unit_net_value": "已公布单位净值（上一交易日）",
            "reported_growth_rate": "已公布日增长率(%)",
            "estimation_deviation_rate": "估算偏差(%)，反映估算与实际的差距",
        },
    },
    {
        "name": "get_fund_value_estimation_list",
        "description": "获取指定类型基金的全量净值估算列表。适合批量筛选：按估算增长率排序找领涨基金，或按估算偏差筛选。",
        "path": "/api/market/fund_public/value_estimation_list",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "fund_type": {
                    "type": "string",
                    "description": "基金类型，默认 all, 包含股票型, 混合型, 债券型, 指数型, QDII, ETF联接, LOF, 场内交易基金",
                    "enum": ["all", "stock", "mixed", "bond", "index", "qdii", "etf_link", "lof", "exchange_traded_fund"],
                },
            },
            "required": [],
        },
        "returns": {
            "fund_code": "基金代码",
            "fund_name": "基金名称",
            "estimation_value": "盘中估算净值",
            "estimation_growth_rate": "估算增长率(%)",
            "reported_unit_net_value": "已公布单位净值",
            "estimation_deviation_rate": "估算偏差(%)",
        },
    },
    {
        "name": "get_fund_rank",
        "description": "获取开放式基金业绩排行榜。按基金类型分类，展示各阶段收益排名（近1周/1月/3月/6月/1年/2年/3年/成立以来）。是基金筛选和对比的首选接口。",
        "path": "/api/market/fund_public/rank",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "fund_type": {
                    "type": "string",
                    "description": "基金类型。all=全部, stock=股票型, mixed=混合型, bond=债券型, index=指数型, qdii=QDII, fof=FOF",
                    "enum": ["all", "stock", "mixed", "bond", "index", "qdii", "fof"],
                },
                "order_by": {
                    "type" : "string",
                    "description": "排序字段。change_1w=近1周收益, change_1m=近1月收益, change_3m=近3月收益, change_6m=近6月收益, change_1y=近1年收益, change_2y=近2年收益, change_3y=近3年收益, change_ytd=今年以来收益, change_since_inception=成立以来收益",
                    "enum": ["change_1w", "change_1m", "change_3m", "change_6m", "change_1y", "change_2y", "change_3y", "change_ytd", "change_since_inception"],
                }
            },
            "required": [],
        },
        "returns": {
            "fund_code": "基金代码",
            "fund_name": "基金简称",
            "date": "净值日期",
            "unit_net_value": "单位净值",
            "accumulated_net_value": "累计净值",
            "daily_growth_rate": "日增长率(%)",
            "change_1w": "近1周收益(%)",
            "change_1m": "近1月收益(%)",
            "change_3m": "近3月收益(%)",
            "change_6m": "近6月收益(%)",
            "change_1y": "近1年收益(%)",
            "change_2y": "近2年收益(%)",
            "change_3y": "近3年收益(%)",
            "change_ytd": "今年以来收益(%)",
            "change_since_inception": "成立以来收益(%)",
            "fee": "手续费(%)",
        },
    },
    {
        "name": "get_fund_info_index",
        "description": "获取指数基金信息。可按指数类别（沪深/行业/大盘/中盘/小盘/股票/债券）和投资方式（被动/增强）筛选。包含各阶段收益、跟踪标的、跟踪方式。是对指数基金进行对比筛选的专用接口。",
        "path": "/api/market/fund_public/info_index",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "指数类别",
                    "enum": ["all", "hs_index", "industry_theme", "large_cap_index", "mid_cap_index", "small_cap_index", "stock_index", "bond_index"],
                },
                "indicator": {
                    "type": "string",
                    "description": "投资方式。passive=被动指数型, enhanced=增强指数型",
                    "enum": ["all", "passive", "enhanced"],
                },
            },
            "required": [],
        },
        "returns": {
            "fund_code": "基金代码",
            "fund_name": "基金简称",
            "unit_net_value": "单位净值",
            "date": "净值日期",
            "daily_growth_rate": "日增长率(%)",
            "change_1w": "近1周收益(%)",
            "change_1m": "近1月收益(%)",
            "change_3m": "近3月收益(%)",
            "change_6m": "近6月收益(%)",
            "change_1y": "近1年收益(%)",
            "change_2y": "近2年收益(%)",
            "change_3y": "近3年收益(%)",
            "change_ytd": "今年以来收益(%)",
            "change_since_inception": "成立以来收益(%)",
            "tracking_index": "跟踪标的指数",
            "tracking_method": "跟踪方式",
            "min_purchase_amount": "起购金额",
            "fee": "手续费(%)",
        },
    },
    {
        "name": "get_fund_individual_basic_info",
        "description": "获取单只基金的基本信息概览：成立时间、最新规模、基金公司、基金经理、托管银行、基金类型、评级、投资策略与目标。适合在分析一只基金前先了解其背景。",
        "path": "/api/market/fund_public/individual_basic_info",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "基金代码",
                },
            },
            "required": ["code"],
        },
        "returns": {
            "fund_code": "基金代码",
            "fund_name": "基金全称",
            "fund_type": "基金类型",
            "inception_date": "成立时间",
            "latest_aum": "最新规模",
            "fund_company": "基金公司",
            "fund_manager": "基金经理",
            "custodian_bank": "托管银行",
            "fund_rating": "基金评级",
            "rating_agency": "评级机构",
            "investment_strategy": "投资策略",
            "investment_objective": "投资目标",
        },
    },
    {
        "name": "get_fund_individual_detail_hold",
        "description": "获取基金持仓的资产类型分布（股票、债券、现金等各类资产的仓位占比）。用于分析基金的资产配置结构和风险敞口。",
        "path": "/api/market/fund_public/individual_detail_hold",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "基金代码",
                },
                "date": {
                    "type": "string",
                    "description": "报告日期，格式 YYYYMMDD。不传则返回最新一期",
                },
            },
            "required": ["code"],
        },
        "returns": {
            "asset_type": "资产类型",
            "pct": "仓位占比(%)",
        },
    },
    {
        "name": "get_fund_portfolio_industry_allocation",
        "description": "获取基金持仓的行业配置分布。展示在各行业的市值和占净值比例，用于分析基金的投资风格和行业偏好。",
        "path": "/api/market/fund_public/portfolio_industry_allocation",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "基金代码",
                },
                "year": {
                    "type": "string",
                    "description": "年份，如 2025, 默认为当前年份",
                },
            },
            "required": ["code"],
        },
        "returns": {
            "sequence": "序号",
            "industry_category": "行业类别",
            "pct": "占净值比例(%)",
            "market_value": "市值",
            "as_of_date": "截止时间",
        },
    },
    {
        "name": "get_fund_portfolio_hold_stock",
        "description": "获取基金持仓股票明细（仅股票）。展示每只股票的持股数、持仓市值和占净值比例，比 portfolio_holds 的持仓数据更精炼（仅含股票，不含其他资产）。",
        "path": "/api/market/fund_public/portfolio_hold_stock",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "基金代码",
                },
                "year": {
                    "type": "string",
                    "description": "年份，如 2025, 默认为当前年份",
                },
            },
            "required": ["code"],
        },
        "returns": {
            "sequence": "序号",
            "stock_code": "股票代码",
            "stock_name": "股票名称",
            "pct": "占净值比例(%)",
            "hold_shares": "持股数",
            "hold_market_value": "持仓市值",
            "quarter": "季度",
        },
    },
    {
        "name": "get_fund_portfolio_hold_bond",
        "description": "获取基金持仓债券明细。展示每只债券的持仓市值和占净值比例，用于分析债券型基金的信用风险暴露和久期策略。",
        "path": "/api/market/fund_public/portfolio_hold_bond",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "基金代码",
                },
                "year": {
                    "type": "string",
                    "description": "年份，如 2025, 默认为当前年份",
                },
            },
            "required": ["code"],
        },
        "returns": {
            "sequence": "序号",
            "bond_code": "债券代码",
            "bond_name": "债券名称",
            "pct": "占净值比例(%)",
            "hold_market_value": "持仓市值",
            "quarter": "季度",
        },
    },

    # =====================================================================
    # 债券
    # =====================================================================
    {
        "name": "get_bond_spot_quote",
        "description": "获取全市场债券实时报价行情。包含各报价机构的买入/卖出净价和对应收益率。适合查看债券的市场定价和流动性。",
        "path": "/api/market/bond/spot_quote",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "returns": {
            "bond_name": "债券简称",
            "bond_code": "债券代码",
            "quote_institution": "报价机构",
            "buying_clean_price": "买入净价",
            "selling_clean_price": "卖出净价",
            "buying_yield": "买入收益率(%)",
            "selling_yield": "卖出收益率(%)",
        },
    },
    {
        "name": "get_bond_spot_deal",
        "description": "获取全市场债券成交行情。包含成交净价、最新收益率、涨跌幅、加权收益率和成交量。适合分析债券的实际交易活跃度和价格走势。",
        "path": "/api/market/bond/spot_deal",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "returns": {
            "bond_name": "债券简称",
            "bond_code": "债券代码",
            "deal_clean_price": "成交净价",
            "latest_yield": "最新收益率(%)",
            "change": "涨跌",
            "weighted_yield": "加权收益率(%)",
            "volume": "交易量",
        },
    },
    {
        "name": "get_bond_spot_quote_search",
        "description": "按债券代码或名称搜索单只债券的实时报价行情。返回各报价机构的买入/卖出净价和收益率。",
        "path": "/api/market/bond/spot_quote_search",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "bond_code": {
                    "type": "string",
                    "description": "债券代码。与 bond_name 二选一",
                },
                "bond_name": {
                    "type": "string",
                    "description": "债券名称/简称。与 bond_code 二选一",
                },
            },
            "required": [],
        },
        "returns": {
            "bond_name": "债券简称",
            "bond_code": "债券代码",
            "quote_institution": "报价机构",
            "buying_clean_price": "买入净价",
            "selling_clean_price": "卖出净价",
            "buying_yield": "买入收益率(%)",
            "selling_yield": "卖出收益率(%)",
        },
    },
    {
        "name": "get_bond_spot_deal_search",
        "description": "按债券代码或名称搜索单只债券的成交行情。包含成交净价、最新收益率、涨跌幅和加权收益率。适用于关注具体个债的成交状况。",
        "path": "/api/market/bond/spot_deal_search",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "bond_code": {
                    "type": "string",
                    "description": "债券代码。与 bond_name 二选一",
                },
                "bond_name": {
                    "type": "string",
                    "description": "债券名称/简称。与 bond_code 二选一",
                },
            },
            "required": [],
        },
        "returns": {
            "bond_name": "债券简称",
            "bond_code": "债券代码",
            "deal_clean_price": "成交净价",
            "latest_yield": "最新收益率(%)",
            "change": "涨跌",
            "weighted_yield": "加权收益率(%)",
            "volume": "交易量",
        },
    },
    {
        "name": "get_bond_info_search",
        "description": "搜索债券基本信息。可按债券名称、代码、发行主体、债券类型、付息方式、发行年份、债项评级、主承销商等多维度筛选。适合寻找符合特定条件的债券。",
        "path": "/api/market/bond/info_search",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "bond_name": {
                    "type": "string",
                    "description": "债券简称，支持模糊搜索",
                },
                "bond_code": {
                    "type": "string",
                    "description": "债券代码",
                },
                "bond_issue": {
                    "type": "string",
                    "description": "发行人/受托机构",
                },
                "bond_type": {
                    "type": "string",
                    "description": "债券类型，如 国债、企业债、中期票据 等",
                },
                "coupon_type": {
                    "type": "string",
                    "description": "付息方式，如 附息、贴现、利随本清 等",
                },
                "issue_year": {
                    "type": "string",
                    "description": "发行年份，如 2025",
                },
                "grade": {
                    "type": "string",
                    "description": "最新债项评级，如 AAA、AA+、AA 等",
                },
                "underwriter": {
                    "type": "string",
                    "description": "主承销商",
                },
            },
            "required": [],
        },
        "returns": {
            "bond_name": "债券简称",
            "bond_code": "债券代码",
            "issuer_or_trustee": "发行人/受托机构",
            "bond_type": "债券类型",
            "issue_date": "发行日期",
            "latest_bond_rating": "最新债项评级",
            "query_code": "查询代码",
        },
    },
    {
        "name": "get_bond_china_yield",
        "description": "获取中国国债收益率曲线数据。返回各期限（3月/6月/1年/3年/5年/7年/10年/30年）的收益率。日期范围不能超过1年。用于分析利率期限结构、判断市场对宏观经济的预期。",
        "path": "/api/market/bond/china_yield",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "起始日期，格式 YYYYMMDD，如 20250101。与 end_date 间隔不超过1年",
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期，格式 YYYYMMDD，如 20250528",
                },
            },
            "required": ["start_date", "end_date"],
        },
        "returns": {
            "bond_name": "债券简称",
            "bond_code": "债券代码",
            "curve_name": "收益率曲线名称",
            "date": "日期",
            "yield_3m": "3月期收益率(%)",
            "yield_6m": "6月期收益率(%)",
            "yield_1y": "1年期收益率(%)",
            "yield_3y": "3年期收益率(%)",
            "yield_5y": "5年期收益率(%)",
            "yield_7y": "7年期收益率(%)",
            "yield_10y": "10年期收益率(%)",
            "yield_30y": "30年期收益率(%)",
        },
    },
    {
        "name": "get_bond_china_yield_search",
        "description": "按曲线名称搜索中国国债收益率曲线数据。支持模糊匹配曲线名称（如 国债、政策性银行债 等）。可用于关注特定类型债券的收益率曲线。",
        "path": "/api/market/bond/china_yield_search",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "curve_name": {
                    "type": "string",
                    "description": "曲线名称，支持模糊匹配，如 国债、政策性银行债、中短期票据 等",
                },
                "start_date": {
                    "type": "string",
                    "description": "起始日期，格式 YYYYMMDD。与 end_date 间隔不超过1年",
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期，格式 YYYYMMDD",
                },
            },
            "required": ["curve_name", "start_date", "end_date"],
        },
        "returns": {
            "bond_name": "债券简称",
            "bond_code": "债券代码",
            "curve_name": "收益率曲线名称",
            "date": "日期",
            "yield_3m": "3月期收益率(%)",
            "yield_6m": "6月期收益率(%)",
            "yield_1y": "1年期收益率(%)",
            "yield_3y": "3年期收益率(%)",
            "yield_5y": "5年期收益率(%)",
            "yield_7y": "7年期收益率(%)",
            "yield_10y": "10年期收益率(%)",
            "yield_30y": "30年期收益率(%)",
        },
    },
    {
        "name": "get_bond_name_by_code",
        "description": "根据债券代码查询对应的债券名称/简称。适合在只有代码时需要确认债券全称的场景。",
        "path": "/api/market/bond/get_name_by_code",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "bond_code": {
                    "type": "string",
                    "description": "债券代码",
                },
            },
            "required": ["bond_code"],
        },
        "returns": {
            "_note": "直接返回债券名称字符串，而非对象数组",
        },
    },

    # =====================================================================
    # 加密货币
    # =====================================================================
    {
        "name": "get_crypto_books",
        "description": "获取加密货币订单簿深度数据（买卖盘口挂单）。",
        "path": "/api/market/crypto/books",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "交易对，如 BTC-USDT",
                },
            },
            "required": ["symbol"],
        },
        "returns": {
            "bids": "买盘挂单列表 [[价格, 数量], ...]",
            "asks": "卖盘挂单列表 [[价格, 数量], ...]",
            "timestamp": "数据时间戳",
        },
    },
    {
        "name": "get_crypto_ticker",
        "description": "获取加密货币实时行情（最新价、涨跌幅、24H 最高最低价、成交量）。",
        "path": "/api/market/crypto/ticker",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "交易对，如 BTC-USDT",
                },
            },
            "required": ["symbol"],
        },
        "returns": {
            "symbol": "交易对",
            "last": "最新价",
            "change_pct": "24H涨跌幅(%)",
            "high_24h": "24H最高价",
            "low_24h": "24H最低价",
            "vol_24h": "24H成交量",
        },
    },
    {
        "name": "get_crypto_klines",
        "description": "获取加密货币历史K线数据（OHLCV）。",
        "path": "/api/market/crypto/klines",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "交易对，如 BTC-USDT",
                },
                "market_type": {
                    "type": "string",
                    "description": "市场类型。SPOT=现货, SWAP=合约",
                    "enum": ["SPOT", "SWAP"],
                },
                "interval": {
                    "type": "string",
                    "description": "K线间隔",
                    "enum": ["1m", "5m", "15m", "30m", "1H", "4H", "1D"],
                },
                "start_time": {
                    "type": "string",
                    "description": "起始时间",
                },
                "end_time": {
                    "type": "string",
                    "description": "结束时间",
                },
                "limit": {
                    "type": "integer",
                    "description": "返回条数上限，默认 1000",
                },
            },
            "required": ["symbol", "start_time", "end_time"],
        },
        "returns": {
            "timestamp": "K线时间",
            "open": "开盘价",
            "high": "最高价",
            "low": "最低价",
            "close": "收盘价",
            "volume": "成交量",
        },
    },
    {
        "name": "get_crypto_ma",
        "description": "获取加密货币K线及移动平均线指标。可自定义均线周期。",
        "path": "/api/market/crypto/ma",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "交易对，如 BTC-USDT",
                },
                "market_type": {
                    "type": "string",
                    "description": "市场类型",
                    "enum": ["SPOT", "SWAP"],
                },
                "interval": {
                    "type": "string",
                    "description": "K线间隔",
                    "enum": ["1m", "5m", "15m", "30m", "1H", "4H", "1D"],
                },
                "ma_periods": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "均线周期列表，如 [5, 10, 20, 60]",
                },
                "start_time": {
                    "type": "string",
                    "description": "起始时间",
                },
                "end_time": {
                    "type": "string",
                    "description": "结束时间",
                },
                "limit": {
                    "type": "integer",
                    "description": "返回条数上限，默认 500",
                },
            },
            "required": ["symbol"],
        },
        "returns": {
            "timestamp": "K线时间",
            "open": "开盘价",
            "high": "最高价",
            "low": "最低价",
            "close": "收盘价",
            "volume": "成交量",
            "_ma_note": "ma{N} 列：N周期移动平均线，N由请求的 ma_periods 决定",
        },
    },

    # =====================================================================
    # 全球市场 — 外汇汇率
    # =====================================================================
    {
        "name": "get_exchange_rate",
        "description": "查询两种货币之间的实时汇率。返回1单位源货币可兑换的目标货币数量。",
        "path": "/api/market/global/exchange_rate/rate",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "from_currency": {
                    "type": "string",
                    "description": "源货币代码，如 USD、CNY、EUR、JPY、GBP 等",
                },
                "to_currency": {
                    "type": "string",
                    "description": "目标货币代码，如 USD、CNY、EUR、JPY、GBP 等",
                },
            },
            "required": ["from_currency", "to_currency"],
        },
        "returns": {
            "from_currency": "源货币代码",
            "to_currency": "目标货币代码",
            "rate": "汇率（1 from_currency = rate to_currency）",
        },
    },
    {
        "name": "get_currency_convert",
        "description": "货币金额转换。将指定金额从一种货币转换为另一种货币。",
        "path": "/api/market/global/exchange_rate/convert",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "要转换的金额",
                },
                "from_currency": {
                    "type": "string",
                    "description": "源货币代码，如 USD",
                },
                "to_currency": {
                    "type": "string",
                    "description": "目标货币代码，如 CNY",
                },
            },
            "required": ["amount", "from_currency", "to_currency"],
        },
        "returns": {
            "amount": "原始金额",
            "from_currency": "源货币代码",
            "to_currency": "目标货币代码",
            "converted_amount": "转换后金额",
        },
    },
    {
        "name": "get_all_exchange_rates",
        "description": "获取基础货币对所有其他主要货币的汇率报价。返回一个字典，key为目标货币代码，value为汇率。适合一次获取某种货币对所有货币的汇率全景。",
        "path": "/api/market/global/exchange_rate/all_rates",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "base_currency": {
                    "type": "string",
                    "description": "基础货币代码，如 USD",
                },
            },
            "required": ["base_currency"],
        },
        "returns": {
            "base_currency": "基础货币代码",
            "rates": "汇率字典 {目标货币代码: 汇率, ...}，如 {'CNY': 7.25, 'EUR': 0.92, ...}",
        },
    },
    {
        "name": "get_exchange_rate_history",
        "description": "查询历史上某一天基础货币对所有其他货币的汇率。返回指定日期的全部汇率报价。适合回溯历史汇率水平。",
        "path": "/api/market/global/exchange_rate/history",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "from_currency": {
                    "type": "string",
                    "description": "源货币代码，如 USD",
                },
                "to_currency": {
                    "type": "string",
                    "description": "目标货币代码，如 CNY",
                },
                "query_date": {
                    "type": "string",
                    "description": "查询日期，格式 YYYY-MM-DD，如 2025-06-01",
                },
            },
            "required": ["from_currency", "to_currency", "query_date"],
        },
        "returns": {
            "from_currency": "源货币代码",
            "to_currency": "目标货币代码",
            "query_date": "查询日期",
            "rates": "该日期的基础货币对全部货币汇率字典 {货币代码: 汇率, ...}",
        },
    },

    # =====================================================================
    # 全球市场 — 全球指数
    # =====================================================================
    {
        "name": "get_global_index_list",
        "description": "获取支持的全球指数列表。包含14个主要指数：S&P 500、纳斯达克、道琼斯、富时100、日经225、恒生、德国DAX、法国CAC40、欧洲斯托克50、澳洲ASX200、韩国KOSPI、印度NIFTY50、巴西BOVESPA、罗素2000。",
        "path": "/api/market/global/index/list",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "returns": {
            "ticker": "指数代码（如 ^GSPC、^HSI），用于其他指数接口的入参",
            "name": "指数名称（中文/英文）",
            "region": "所属国家/地区",
            "currency": "计价货币",
        },
    },
    {
        "name": "get_global_index_quote",
        "description": "获取单个全球指数的最新实时行情。包含最新价、涨跌幅、涨跌额、当日最高最低价、成交量等。",
        "path": "/api/market/global/index/quote",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "指数代码，如 ^GSPC（S&P 500）、^HSI（恒生）、^N225（日经225）。完整列表见 get_global_index_list",
                },
            },
            "required": ["ticker"],
        },
        "returns": {
            "ticker": "指数代码",
            "name": "指数名称",
            "price": "最新价",
            "previous_close": "前收盘价",
            "open": "今日开盘价",
            "day_high": "今日最高价",
            "day_low": "今日最低价",
            "volume": "成交量",
            "change": "涨跌额",
            "change_pct": "涨跌幅(%)",
            "currency": "计价货币",
        },
    },
    {
        "name": "get_global_index_quotes",
        "description": "批量获取多个全球指数的最新行情。一次传入多个指数代码，返回各指数行情，附带地区和货币信息。比逐个调用 get_global_index_quote 效率更高。",
        "path": "/api/market/global/index/quotes",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "指数代码列表，如 ['^GSPC', '^HSI', '^N225']",
                },
            },
            "required": ["tickers"],
        },
        "returns": {
            "ticker": "指数代码",
            "name": "指数名称",
            "price": "最新价",
            "previous_close": "前收盘价",
            "open": "今日开盘价",
            "day_high": "今日最高价",
            "day_low": "今日最低价",
            "volume": "成交量",
            "change": "涨跌额",
            "change_pct": "涨跌幅(%)",
            "currency": "计价货币",
            "region": "所属国家/地区",
        },
    },
    {
        "name": "get_global_index_rank",
        "description": "获取所有全球指数的涨跌幅排行。一次返回全部14个全球指数的最新行情，按涨跌幅(change_pct)从大到小排序。包含最新价、涨跌额、涨跌幅、开盘价、最高价、最低价、成交量等字段。适合快速一览全球市场当日表现、发现领涨/领跌市场。",
        "path": "/api/market/global/index/rank",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "returns": {
            "ticker": "指数代码",
            "name": "指数名称",
            "price": "最新价",
            "previous_close": "前收盘价",
            "open": "今日开盘价",
            "day_high": "今日最高价",
            "day_low": "今日最低价",
            "volume": "成交量",
            "change": "涨跌额",
            "change_pct": "涨跌幅(%)",
            "currency": "计价货币",
            "region": "所属国家/地区",
        },
    },
    {
        "name": "get_global_index_info",
        "description": "获取单个全球指数的详细信息（比 quote 更全面）。除行情外，还包含50日/200日均价、交易所名称、市场类型等。适合深入了解指数背景。",
        "path": "/api/market/global/index/info",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "指数代码，如 ^GSPC",
                },
            },
            "required": ["ticker"],
        },
        "returns": {
            "ticker": "指数代码",
            "name": "指数名称",
            "price": "最新价",
            "previous_close": "前收盘价",
            "open": "今日开盘价",
            "day_high": "今日最高价",
            "day_low": "今日最低价",
            "volume": "成交量",
            "change": "涨跌额",
            "change_pct": "涨跌幅(%)",
            "fifty_day_avg": "50日均价",
            "two_hundred_day_avg": "200日均价",
            "currency": "计价货币",
            "market": "市场类型",
            "exchange": "交易所名称",
        },
    },
    {
        "name": "get_global_index_hist",
        "description": "获取全球指数历史K线数据（OHLCV）。支持指定日期范围或预定义周期，支持日/周/月/小时/分钟K线。适合技术分析、走势图绘制、历史回测。",
        "path": "/api/market/global/index/hist",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "指数代码，如 ^GSPC",
                },
                "period": {
                    "type": "string",
                    "description": "预定义数据周期（与 start_date/end_date 互斥）。1d=1天, 5d=5天, 1mo=1月, 3mo=3月, 6mo=6月, 1y=1年, 2y=2年, 5y=5年, 10y=10年, ytd=年初至今, max=全部",
                    "enum": ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"],
                },
                "start_date": {
                    "type": "string",
                    "description": "起始日期，格式 YYYY-MM-DD。与 period 互斥，需同时传 end_date",
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期，格式 YYYY-MM-DD",
                },
                "interval": {
                    "type": "string",
                    "description": "K线周期，默认 1d",
                    "enum": ["1d", "1wk", "1mo", "1h", "1m"],
                },
            },
            "required": ["ticker"],
        },
        "returns": {
            "date": "交易日期",
            "open": "开盘价",
            "high": "最高价",
            "low": "最低价",
            "close": "收盘价",
            "volume": "成交量",
            "dividends": "分红",
            "stock_splits": "拆股系数",
        },
    },

    # =====================================================================
    # 宏观数据 — 全球经济指标
    # =====================================================================
    {
        "name": "get_macro_countries",
        "description": "获取支持的宏观经济数据国家/地区列表。返回每个国家支持的指标数量。覆盖中国、美国、欧元区、英国、日本、德国、加拿大、澳大利亚等8个国家/地区。",
        "path": "/api/market/macro/countries",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "returns": {
            "country": "国家/地区代码（如 china、usa、euro），用于其他宏观接口的 country 参数",
            "indicator_count": "该国支持的宏观指标数量",
        },
    },
    {
        "name": "get_macro_indicators",
        "description": "获取指定国家（或全部国家）的宏观指标列表。返回每个指标的 key、中文名、描述、输出字段数和可传递的额外参数。是使用宏观数据的第一步——先了解有哪些指标可用。",
        "path": "/api/market/macro/indicators",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "country": {
                    "type": "string",
                    "description": "国家代码，如 china、usa、euro。不传则返回全部国家的指标列表",
                },
            },
            "required": [],
        },
        "returns": {
            "_note": "按国家分组的指标列表。每个指标包含：indicator=指标key(用于后续接口), name=中文名, desc=指标说明, column_count=输出字段数, extra_params=可传递的额外参数及其默认值",
        },
    },
    {
        "name": "get_macro_schema",
        "description": "获取指定宏观指标的完整Schema定义（字段元数据）。返回该指标会输出哪些列，以及每列的中文名和含义。前端可据此渲染表头、图例、数据说明。在调用 get_macro_data 拉取数据前，先用此接口了解数据结构。",
        "path": "/api/market/macro/schema",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "country": {
                    "type": "string",
                    "description": "国家代码，如 china",
                },
                "indicator": {
                    "type": "string",
                    "description": "指标 key，如 cpi、gdp、pmi、ppi。可用的指标列表通过 get_macro_indicators 获取",
                },
            },
            "required": ["country", "indicator"],
        },
        "returns": {
            "country": "国家代码",
            "indicator": "指标 key",
            "name": "指标中文名",
            "desc": "指标描述",
            "extra_params": "可传递的额外参数及默认值",
            "columns": "输出字段定义字典 {key: {name: 中文列名, desc: 字段含义}, ...}",
        },
    },
    {
        "name": "get_macro_data",
        "description": "获取宏观指标的实际数据。返回按时间排序的数据列表，每条记录包含该指标的全部字段。数据字段的含义请先用 get_macro_schema 查询——不同指标的输出列完全不同（如CPI返回全国/城市/农村同比环比，GDP返回总量/增速/三次产业等）。",
        "path": "/api/market/macro/data",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "country": {
                    "type": "string",
                    "description": "国家代码，如 china",
                },
                "indicator": {
                    "type": "string",
                    "description": "指标 key，如 cpi、gdp、pmi、money_supply",
                },
                "extra": {
                    "type": "object",
                    "description": "额外参数（可选），用于传递指标特定的筛选条件。具体支持哪些参数见 get_macro_schema 返回的 extra_params。例如中国CPI可传 city_first='北京', city_second='上海' 来获取特定城市的CPI数据",
                },
            },
            "required": ["country", "indicator"],
        },
        "returns": {
            "_note": "数据字段取决于指标，不同指标返回的列完全不同。使用前务必先调用 get_macro_schema 获取字段定义。例如中国CPI包含 month/national_yoy/national_mom/city_yoy/city_mom/rural_yoy/rural_mom 等13列，GDP包含 gdp/yoy_change/primary_industry/secondary_industry/tertiary_industry 等9列",
        },
    },
]


def get_all_functions():
    """返回所有接口的函数定义列表。"""
    return FUNCTIONS


def get_functions_by_tag(tag: str):
    """按标签筛选函数。tag 为 stock / fund / bond / crypto。"""
    prefix_map = {
        "stock": "get_stock",
        "fund": "get_fund",
        "bond": "get_bond",
        "crypto": "get_crypto",
    }
    prefix = prefix_map.get(tag)
    if prefix is None:
        return []
    return [f for f in FUNCTIONS if f["name"].startswith(prefix)]
