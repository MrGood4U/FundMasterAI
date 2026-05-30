"""
Portfolio-backend 全部接口的 Function Calling 定义。

每个函数包含 LLM agent 所需的 name / description / parameters / returns，
以及路由元信息（path / method），agent 可据此生成 HTTP 请求并解析响应。

所有接口的 HTTP 响应格式统一为:
  {"code": 200, "data": ..., "message": "success"}
"""

FUNCTIONS = [
    # =====================================================================
    # Transaction 交易
    # =====================================================================
    {
        "name": "create_transaction",
        "description": "创建一条交易记录，记录买入或卖出某资产的交易明细。",
        "path": "/api/portfolio/transaction/create",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "asset_type": {
                    "type": "string",
                    "description": "资产类型",
                    "enum": ["stock", "fund", "bond", "crypto"],
                },
                "asset_code": {
                    "type": "string",
                    "description": "资产代码，如 600519（股票）、000001（基金）、BTCUSDT（加密货币）",
                },
                "asset_name": {
                    "type": "string",
                    "description": "资产名称（冗余字段，便于展示），如 贵州茅台",
                },
                "trans_type": {
                    "type": "string",
                    "description": "交易方向",
                    "enum": ["buy", "sell"],
                },
                "price": {
                    "type": "number",
                    "description": "成交单价",
                },
                "quantity": {
                    "type": "number",
                    "description": "成交数量（股/份/币）",
                },
                "fee": {
                    "type": "number",
                    "description": "手续费，默认为 0",
                },
                "trans_date": {
                    "type": "string",
                    "description": "交易日期，格式 YYYY-MM-DD",
                },
                "portfolio_tag": {
                    "type": "string",
                    "description": "投资组合标签，如 long-term / short-term / grid / DCA",
                },
                "notes": {
                    "type": "string",
                    "description": "备注信息",
                },
            },
            "required": ["asset_type", "asset_code", "trans_type", "price", "quantity", "trans_date"],
        },
        "returns": {
            "id": "交易记录ID",
        },
    },
    {
        "name": "get_transaction",
        "description": "按ID查询单条交易记录的详细信息。",
        "path": "/api/portfolio/transaction/{trans_id}",
        "method": "GET",
        "parameters": {
            "type": "object",
            "properties": {
                "trans_id": {
                    "type": "integer",
                    "description": "交易记录ID，作为URL路径参数传递",
                },
            },
            "required": ["trans_id"],
        },
        "returns": {
            "id": "交易记录ID",
            "asset_type": "资产类型（stock/fund/bond/crypto）",
            "asset_code": "资产代码",
            "asset_name": "资产名称",
            "trans_type": "交易方向（buy/sell）",
            "price": "成交单价",
            "quantity": "成交数量",
            "fee": "手续费",
            "trans_date": "交易日期",
            "portfolio_tag": "投资组合标签",
            "notes": "备注",
            "created_at": "创建时间",
            "updated_at": "更新时间",
        },
    },
    {
        "name": "update_transaction",
        "description": "更新一条交易记录的部分字段，只传需要修改的字段即可。",
        "path": "/api/portfolio/transaction/update",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "trans_id": {
                    "type": "integer",
                    "description": "交易记录ID",
                },
                "asset_name": {
                    "type": "string",
                    "description": "资产名称",
                },
                "price": {
                    "type": "number",
                    "description": "成交单价",
                },
                "quantity": {
                    "type": "number",
                    "description": "成交数量",
                },
                "fee": {
                    "type": "number",
                    "description": "手续费",
                },
                "trans_date": {
                    "type": "string",
                    "description": "交易日期，格式 YYYY-MM-DD",
                },
                "portfolio_tag": {
                    "type": "string",
                    "description": "投资组合标签",
                },
                "notes": {
                    "type": "string",
                    "description": "备注信息",
                },
            },
            "required": ["trans_id"],
        },
        "returns": {
            "_note": "更新成功返回空对象 {}，失败返回错误信息",
        },
    },
    {
        "name": "delete_transaction",
        "description": "删除一条交易记录，操作不可撤销。",
        "path": "/api/portfolio/transaction/delete",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "trans_id": {
                    "type": "integer",
                    "description": "交易记录ID",
                },
            },
            "required": ["trans_id"],
        },
        "returns": {
            "_note": "删除成功返回空对象 {}，失败返回错误信息",
        },
    },
    {
        "name": "list_transactions",
        "description": "分页查询交易记录列表，可按资产类型、代码、交易方向、日期范围筛选。用于查看交易历史，不适合做盈亏计算（盈亏计算请用 get_holdings）。",
        "path": "/api/portfolio/transaction/list",
        "method": "GET",
        "parameters": {
            "type": "object",
            "properties": {
                "asset_type": {
                    "type": "string",
                    "description": "资产类型筛选",
                    "enum": ["stock", "fund", "bond", "crypto"],
                },
                "asset_code": {
                    "type": "string",
                    "description": "资产代码筛选",
                },
                "trans_type": {
                    "type": "string",
                    "description": "交易方向筛选",
                    "enum": ["buy", "sell"],
                },
                "start_date": {
                    "type": "string",
                    "description": "起始日期，格式 YYYY-MM-DD",
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期，格式 YYYY-MM-DD",
                },
                "page": {
                    "type": "integer",
                    "description": "页码，从 1 开始，默认 1",
                },
                "page_size": {
                    "type": "integer",
                    "description": "每页条数，默认 20",
                },
            },
            "required": [],
        },
        "returns": {
            "items": "交易记录数组，每条包含 id/asset_type/asset_code/asset_name/trans_type/price/quantity/fee/trans_date/portfolio_tag/notes/created_at/updated_at",
            "total": "符合筛选条件的总条数",
            "page": "当前页码",
            "page_size": "每页条数",
        },
    },

    # =====================================================================
    # Holding 持仓
    # =====================================================================
    {
        "name": "get_holdings",
        "description": "获取当前持仓列表，自动聚合所有交易记录计算持仓数量、平均成本、市值和未实现盈亏。每只持仓资产会自动附带实时行情数据（当前价、涨跌幅等）。仅返回持仓数量大于0的资产。",
        "path": "/api/portfolio/holding/list",
        "method": "GET",
        "parameters": {
            "type": "object",
            "properties": {
                "asset_type": {
                    "type": "string",
                    "description": "资产类型筛选",
                    "enum": ["stock", "fund", "bond", "crypto"],
                },
                "page": {
                    "type": "integer",
                    "description": "页码，从 1 开始，默认 1",
                },
                "page_size": {
                    "type": "integer",
                    "description": "每页条数，默认 20",
                },
            },
            "required": [],
        },
        "returns": {
            "items": "持仓记录数组",
            "total": "持仓总数",
            "page": "当前页码",
            "page_size": "每页条数",
            "_item_fields": {
                "asset_type": "资产类型",
                "asset_code": "资产代码",
                "asset_name": "资产名称",
                "total_quantity": "持仓数量（买入-卖出）",
                "avg_cost": "加权平均成本价（含手续费）",
                "total_cost": "持仓总成本（含手续费）",
                "portfolio_tags": "关联的投资组合标签列表",
                "current_price": "实时当前价",
                "market_value": "持仓市值（数量×当前价）",
                "unrealized_pnl": "未实现盈亏（市值-总成本）",
                "unrealized_pnl_pct": "未实现盈亏百分比",
                "change_pct": "当日涨跌幅（来自行情）",
                "change_amount": "当日涨跌额（来自行情）",
            },
        },
    },
    {
        "name": "get_holding_detail",
        "description": "获取某只资产的持仓明细，包含持仓汇总信息、逐笔交易记录、以及每笔买入的批次盈亏（基于当前价格计算）。",
        "path": "/api/portfolio/holding/detail",
        "method": "GET",
        "parameters": {
            "type": "object",
            "properties": {
                "asset_type": {
                    "type": "string",
                    "description": "资产类型",
                    "enum": ["stock", "fund", "bond", "crypto"],
                },
                "asset_code": {
                    "type": "string",
                    "description": "资产代码",
                },
            },
            "required": ["asset_type", "asset_code"],
        },
        "returns": {
            "_extends": "包含 get_holdings 返回的所有汇总字段",
            "transactions": "该资产的全部交易记录数组，每笔买入含 batch_pnl（批次盈亏金额）和 batch_pnl_pct（批次盈亏百分比）",
        },
    },

    # =====================================================================
    # Alert 价格告警
    # =====================================================================
    {
        "name": "create_alert",
        "description": "创建一条价格告警。支持两种触发模式：price（绝对价格阈值）和 pct（相对持仓成本的百分比变化）。告警触发后系统会自动禁用该告警并通过电话/邮件通知用户。",
        "path": "/api/portfolio/alert/create",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "asset_type": {
                    "type": "string",
                    "description": "资产类型",
                    "enum": ["stock", "fund", "bond", "crypto"],
                },
                "asset_code": {
                    "type": "string",
                    "description": "资产代码",
                },
                "alert_type": {
                    "type": "string",
                    "description": "告警类型。stop_profit=止盈，stop_loss=止损，price_above=价格上涨突破，price_below=价格下跌突破",
                    "enum": ["stop_profit", "stop_loss", "price_above", "price_below"],
                },
                "trigger_mode": {
                    "type": "string",
                    "description": "触发模式。price=绝对价格阈值，需传trigger_price；pct=百分比变化阈值，需传trigger_pct（基于加权平均持仓成本计算）",
                    "enum": ["price", "pct"],
                },
                "trigger_price": {
                    "type": "number",
                    "description": "触发价格（price模式必填）。当当前价>=此价格时触发price_above/stop_profit，<=时触发price_below/stop_loss",
                },
                "trigger_pct": {
                    "type": "number",
                    "description": "触发百分比（pct模式必填），小数形式。如0.15表示15%。基准为加权平均持仓成本，变化超过此百分比时触发",
                },
                "reference_trans_id": {
                    "type": "integer",
                    "description": "指定参考的交易ID（可选）。若指定，pct模式以该笔交易价格作为成本基准；不指定则自动使用全部买入的加权平均成本",
                },
                "notify_phone": {
                    "type": "boolean",
                    "description": "是否电话通知，默认false。需用户已设置并验证手机号",
                },
                "notify_email": {
                    "type": "boolean",
                    "description": "是否邮件通知，默认false。需用户已设置并验证邮箱",
                },
                "notes": {
                    "type": "string",
                    "description": "备注信息",
                },
            },
            "required": ["asset_type", "asset_code", "alert_type", "trigger_mode"],
        },
        "returns": {
            "id": "告警记录ID",
        },
    },
    {
        "name": "get_alert",
        "description": "按ID查询单条告警记录的详细信息。",
        "path": "/api/portfolio/alert/{alert_id}",
        "method": "GET",
        "parameters": {
            "type": "object",
            "properties": {
                "alert_id": {
                    "type": "integer",
                    "description": "告警记录ID，作为URL路径参数传递",
                },
            },
            "required": ["alert_id"],
        },
        "returns": {
            "id": "告警记录ID",
            "asset_type": "资产类型",
            "asset_code": "资产代码",
            "alert_type": "告警类型（stop_profit/stop_loss/price_above/price_below）",
            "trigger_mode": "触发模式（price/pct）",
            "trigger_price": "触发价格阈值",
            "trigger_pct": "触发百分比阈值",
            "reference_trans_id": "参考交易ID",
            "notify_phone": "是否电话通知",
            "notify_email": "是否邮件通知",
            "is_enabled": "是否启用",
            "notified_at": "上次触发通知时间",
            "notes": "备注",
            "created_at": "创建时间",
            "updated_at": "更新时间",
        },
    },
    {
        "name": "update_alert",
        "description": "更新一条告警记录的部分字段。可用于修改阈值、切换通知方式、重新启用已触发的告警等。",
        "path": "/api/portfolio/alert/update",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "alert_id": {
                    "type": "integer",
                    "description": "告警记录ID",
                },
                "alert_type": {
                    "type": "string",
                    "description": "告警类型",
                    "enum": ["stop_profit", "stop_loss", "price_above", "price_below"],
                },
                "trigger_mode": {
                    "type": "string",
                    "description": "触发模式",
                    "enum": ["price", "pct"],
                },
                "trigger_price": {
                    "type": "number",
                    "description": "触发价格阈值",
                },
                "trigger_pct": {
                    "type": "number",
                    "description": "触发百分比阈值（小数形式）",
                },
                "reference_trans_id": {
                    "type": "integer",
                    "description": "参考交易ID",
                },
                "notify_phone": {
                    "type": "boolean",
                    "description": "是否电话通知",
                },
                "notify_email": {
                    "type": "boolean",
                    "description": "是否邮件通知",
                },
                "is_enabled": {
                    "type": "boolean",
                    "description": "是否启用告警。已触发的告警会自动设为false，需要手动设为true重新激活",
                },
                "notes": {
                    "type": "string",
                    "description": "备注信息",
                },
            },
            "required": ["alert_id"],
        },
        "returns": {
            "_note": "更新成功返回空对象 {}",
        },
    },
    {
        "name": "delete_alert",
        "description": "删除一条告警记录。",
        "path": "/api/portfolio/alert/delete",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "alert_id": {
                    "type": "integer",
                    "description": "告警记录ID",
                },
            },
            "required": ["alert_id"],
        },
        "returns": {
            "_note": "删除成功返回空对象 {}",
        },
    },
    {
        "name": "list_alerts",
        "description": "分页查询告警记录列表，可按启用状态和资产类型筛选。",
        "path": "/api/portfolio/alert/list",
        "method": "GET",
        "parameters": {
            "type": "object",
            "properties": {
                "is_enabled": {
                    "type": "boolean",
                    "description": "是否启用筛选。传 true/1/yes 查启用的告警，传 false/0/no 查已禁用的告警",
                },
                "asset_type": {
                    "type": "string",
                    "description": "资产类型筛选",
                    "enum": ["stock", "fund", "bond", "crypto"],
                },
                "page": {
                    "type": "integer",
                    "description": "页码，从 1 开始，默认 1",
                },
                "page_size": {
                    "type": "integer",
                    "description": "每页条数，默认 20",
                },
            },
            "required": [],
        },
        "returns": {
            "items": "告警记录数组",
            "total": "符合筛选条件的总条数",
            "page": "当前页码",
            "page_size": "每页条数",
        },
    },

    # =====================================================================
    # Watchlist 自选/关注
    # =====================================================================
    {
        "name": "add_to_watchlist",
        "description": "添加资产到自选列表。如同一资产类型+代码已存在则更新记录（覆盖目标价、优先级等字段）。",
        "path": "/api/portfolio/watchlist/create",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "asset_type": {
                    "type": "string",
                    "description": "资产类型",
                    "enum": ["stock", "fund", "bond", "crypto"],
                },
                "asset_code": {
                    "type": "string",
                    "description": "资产代码",
                },
                "asset_name": {
                    "type": "string",
                    "description": "资产名称",
                },
                "target_price": {
                    "type": "number",
                    "description": "目标买入价格",
                },
                "priority": {
                    "type": "integer",
                    "description": "优先级 0-5，数字越大优先级越高，默认 0",
                },
                "notes": {
                    "type": "string",
                    "description": "备注信息",
                },
            },
            "required": ["asset_type", "asset_code"],
        },
        "returns": {
            "id": "自选记录ID",
        },
    },
    {
        "name": "remove_from_watchlist",
        "description": "从自选列表中移除一条记录。",
        "path": "/api/portfolio/watchlist/delete",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "watchlist_id": {
                    "type": "integer",
                    "description": "自选记录ID",
                },
            },
            "required": ["watchlist_id"],
        },
        "returns": {
            "_note": "删除成功返回空对象 {}",
        },
    },
    {
        "name": "list_watchlist",
        "description": "分页查询自选列表，按优先级降序排列。每条自选资产会自动附带实时行情数据（当前价、涨跌幅等）。",
        "path": "/api/portfolio/watchlist/list",
        "method": "GET",
        "parameters": {
            "type": "object",
            "properties": {
                "asset_type": {
                    "type": "string",
                    "description": "资产类型筛选",
                    "enum": ["stock", "fund", "bond", "crypto"],
                },
                "page": {
                    "type": "integer",
                    "description": "页码，从 1 开始，默认 1",
                },
                "page_size": {
                    "type": "integer",
                    "description": "每页条数，默认 20",
                },
            },
            "required": [],
        },
        "returns": {
            "items": "自选记录数组，每条包含 id/asset_type/asset_code/asset_name/target_price/priority/notes/created_at，以及 price_info（实时行情对象，含current_price/change_pct等）",
            "total": "自选总数",
            "page": "当前页码",
            "page_size": "每页条数",
        },
    },

    # =====================================================================
    # Allocation 资产配置
    # =====================================================================
    {
        "name": "get_current_allocation",
        "description": "获取当前各类资产（stock/fund/bond/crypto）的持仓市值与占比。基于实时行情计算市值，用于了解当前实际配置状态。",
        "path": "/api/portfolio/allocation/current",
        "method": "GET",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "returns": {
            "items": "各类资产配置数组",
            "total_market_value": "总市值",
            "total_cost": "总成本",
            "_item_fields": {
                "asset_type": "资产大类（stock/fund/bond/crypto）",
                "market_value": "该类别持仓总市值",
                "pct": "该类别占总市值的百分比",
                "total_cost": "该类别持仓总成本",
            },
        },
    },
    {
        "name": "set_target_allocation",
        "description": "设定目标资产配置比例。传入各资产类别的目标百分比（总和必须为100）。通常由Agent根据用户风险偏好推荐后调用。例如 risk-averse: {stock:30, fund:30, bond:35, crypto:5}；aggressive: {stock:50, fund:20, bond:10, crypto:20}。",
        "path": "/api/portfolio/allocation/target",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "stock": {
                    "type": "number",
                    "description": "股票目标占比(%)",
                },
                "fund": {
                    "type": "number",
                    "description": "基金目标占比(%)",
                },
                "bond": {
                    "type": "number",
                    "description": "债券目标占比(%)",
                },
                "crypto": {
                    "type": "number",
                    "description": "加密货币目标占比(%)",
                },
            },
            "required": [],
        },
        "returns": {
            "targets": "已保存的目标配置对象",
            "message": "ok",
        },
    },
    {
        "name": "get_target_allocation",
        "description": "读取已保存的目标资产配置比例。Agent 可用于确认用户当前策略后再做出推荐。",
        "path": "/api/portfolio/allocation/target",
        "method": "GET",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "returns": {
            "_note": "返回如 {\"stock\": 40, \"fund\": 30, \"bond\": 20, \"crypto\": 10}，仅包含已设定的资产类别的字段",
        },
    },
    {
        "name": "get_allocation_drift",
        "description": "计算当前配置与目标配置的偏离度。返回每类资产的当前占比、目标占比、差值及状态（超配/低配/正常）。偏离超过5%标记为超配或低配，是触发再平衡的信号。",
        "path": "/api/portfolio/allocation/drift",
        "method": "GET",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "returns": {
            "items": "偏离度数组",
            "total_market_value": "总市值",
            "_item_fields": {
                "asset_type": "资产大类",
                "current_pct": "当前实际占比(%)",
                "target_pct": "目标占比(%)",
                "diff_pct": "差值(当前-目标)，正=超配，负=低配",
                "status": "状态：超配/低配/正常",
            },
        },
    },

    # =====================================================================
    # Sector 行业暴露
    # =====================================================================
    {
        "name": "get_sector_exposure",
        "description": "穿透持仓汇总各行业的市值分布。直接持有的个股按名称关键词归入行业；持有的基金通过调market_backend获取基金持仓明细后再按行业归类。债券和加密货币分别归入'债券'和'加密货币'。",
        "path": "/api/portfolio/sector/exposure",
        "method": "GET",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "returns": {
            "items": "行业分布数组（按市值降序）",
            "total_market_value": "总市值",
            "_item_fields": {
                "sector": "行业名称（医药/科技/金融/消费/新能源/汽车/制造等）",
                "market_value": "该行业持仓市值",
                "pct": "该行业占总市值的百分比",
            },
        },
    },
    {
        "name": "get_sector_concentration",
        "description": "行业与个股集中度分析。返回前3大行业占比、前5大个股占比及风险标记。若单行业占比>70%、单一个股占比>20%或前5个股合计>50%，会给出警告。",
        "path": "/api/portfolio/sector/concentration",
        "method": "GET",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "returns": {
            "top3_sectors": "前3大行业列表（含sector/market_value/pct）",
            "top3_sectors_pct": "前3大行业合计占比(%)",
            "top5_stocks": "前5大个股列表（含code/name/market_value/pct）",
            "top5_stocks_pct": "前5大个股合计占比(%)",
            "warnings": "风险警告字符串数组，如 ['前3大行业占比 85%，集中度过高']",
        },
    },
]


def get_all_functions():
    """返回所有接口的函数定义列表。"""
    return FUNCTIONS


def get_functions_by_tag(tag: str):
    """按标签筛选函数。tag 为 transaction / holding / alert / watchlist / allocation / sector。"""
    prefix_map = {
        "transaction": "create_transaction",
        "holding": "get_holdings",
        "alert": "create_alert",
        "watchlist": "add_to_watchlist",
        "allocation": "get_current_allocation",
        "sector": "get_sector_exposure",
    }
    tag_names = {
        "transaction": ["create_transaction", "get_transaction", "update_transaction",
                        "delete_transaction", "list_transactions"],
        "holding": ["get_holdings", "get_holding_detail"],
        "alert": ["create_alert", "get_alert", "update_alert",
                  "delete_alert", "list_alerts"],
        "watchlist": ["add_to_watchlist", "remove_from_watchlist", "list_watchlist"],
        "allocation": ["get_current_allocation", "set_target_allocation",
                       "get_target_allocation", "get_allocation_drift"],
        "sector": ["get_sector_exposure", "get_sector_concentration"],
    }
    names = tag_names.get(tag)
    if names is None:
        return []
    return [f for f in FUNCTIONS if f["name"] in names]
