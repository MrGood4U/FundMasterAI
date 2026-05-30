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
                    "description": "数据源平台，目前仅支持 eastmoney",
                    "enum": ["eastmoney"],
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
                    "description": "数据源平台，目前仅支持 eastmoney",
                    "enum": ["eastmoney"],
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
