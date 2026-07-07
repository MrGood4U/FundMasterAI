from flask import Blueprint, jsonify, request

from services.global_service import GlobalService

global_bp = Blueprint("global", __name__, url_prefix="/api/market/global")


# ==================================================================
# 外汇 — 汇率查询接口
# ==================================================================

@global_bp.post("/exchange_rate/rate")
def get_exchange_rate():
    """查询两种货币之间的汇率

    Body:
        from_currency: str  — 源货币代码 (如 "USD")
        to_currency: str    — 目标货币代码 (如 "CNY")
    """
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if not data.get("from_currency") or not data.get("to_currency"):
        return jsonify({"message": "from_currency and to_currency are required"}), 404

    service = GlobalService()
    result = service.get_exchange_rate(data["from_currency"], data["to_currency"])
    if result is None:
        return jsonify({"code": 500, "data": None, "message": "failed to fetch exchange rate"}), 500
    return jsonify({"code": 200, "data": {
        "from_currency": data["from_currency"].upper(),
        "to_currency": data["to_currency"].upper(),
        "rate": result,
    }, "message": "success"}), 200


@global_bp.post("/exchange_rate/convert")
def convert_exchange_rate():
    """货币金额转换

    Body:
        amount: float        — 金额
        from_currency: str   — 源货币代码
        to_currency: str     — 目标货币代码
    """
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if (data.get("amount") is None
            or not data.get("from_currency")
            or not data.get("to_currency")):
        return jsonify({"message": "amount, from_currency and to_currency are required"}), 404

    service = GlobalService()
    result = service.convert_currency(
        data["amount"], data["from_currency"], data["to_currency"]
    )
    if result is None:
        return jsonify({"code": 500, "data": None, "message": "failed to convert currency"}), 500
    return jsonify({"code": 200, "data": {
        "amount": data["amount"],
        "from_currency": data["from_currency"].upper(),
        "to_currency": data["to_currency"].upper(),
        "converted_amount": result,
    }, "message": "success"}), 200


@global_bp.post("/exchange_rate/all_rates")
def get_all_exchange_rates():
    """获取基础货币对所有其他货币的汇率

    Body:
        base_currency: str  — 基础货币代码 (如 "USD")
    """
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if not data.get("base_currency"):
        return jsonify({"message": "base_currency is required"}), 404

    service = GlobalService()
    result = service.get_all_rates(data["base_currency"])
    if result is None:
        return jsonify({"code": 500, "data": None, "message": "failed to fetch rates"}), 500
    return jsonify({"code": 200, "data": {
        "base_currency": data["base_currency"].upper(),
        "rates": result,
    }, "message": "success"}), 200


@global_bp.post("/exchange_rate/history")
def get_exchange_rate_history():
    """查询历史某天的汇率

    Body:
        from_currency: str  — 源货币代码
        to_currency: str    — 目标货币代码
        query_date: str     — 日期 "YYYY-MM-DD"
    """
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if (not data.get("from_currency")
            or not data.get("to_currency")
            or not data.get("query_date")):
        return jsonify({
            "message": "from_currency, to_currency and query_date are required"
        }), 404

    service = GlobalService()
    result = service.get_history_rates(
        data["from_currency"], data["to_currency"], data["query_date"]
    )
    if result is None:
        return jsonify({"code": 500, "data": None, "message": "failed to fetch history rates"}), 500
    return jsonify({"code": 200, "data": {
        "from_currency": data["from_currency"].upper(),
        "to_currency": data["to_currency"].upper(),
        "query_date": data["query_date"],
        "rates": result,
    }, "message": "success"}), 200


# ==================================================================
# 全球指数 — 查询接口
# ==================================================================

@global_bp.post("/index/list")
def get_index_list():
    """获取支持的全球指数列表"""
    service = GlobalService()
    result = service.get_supported_indices()
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@global_bp.post("/index/quote")
def get_index_quote():
    """获取单个全球指数的最新行情

    Body:
        ticker: str  — 指数代码 (如 "^GSPC", "^IXIC", "^HSI")
    """
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if not data.get("ticker"):
        return jsonify({"message": "ticker is required"}), 404

    service = GlobalService()
    result = service.get_index_quote(data["ticker"])
    if result is None:
        return jsonify({"code": 500, "data": None, "message": "failed to fetch index quote"}), 500
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@global_bp.post("/index/quotes")
def get_multiple_quotes():
    """批量获取多个全球指数的最新行情

    Body:
        tickers: list[str]  — 指数代码列表
    """
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if not data.get("tickers") or len(data["tickers"]) == 0:
        return jsonify({"message": "tickers is required and must be non-empty"}), 404

    service = GlobalService()
    result = service.get_multiple_quotes(data["tickers"])
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@global_bp.post("/index/info")
def get_index_info():
    """获取单个全球指数的详细信息

    Body:
        ticker: str  — 指数代码
    """
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if not data.get("ticker"):
        return jsonify({"message": "ticker is required"}), 404

    service = GlobalService()
    result = service.get_index_info(data["ticker"])
    if result is None:
        return jsonify({"code": 500, "data": None, "message": "failed to fetch index info"}), 500
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@global_bp.post("/index/hist")
def get_index_hist():
    """获取全球指数的历史K线数据

    Body:
        ticker: str       — 指数代码
        period: str       — 数据周期 (可选, 默认 "1mo")
                            可选: "1d","5d","1mo","3mo","6mo","1y","2y","5y","10y","ytd","max"
        start_date: str   — 起始日期 "YYYY-MM-DD" (与 period 互斥)
        end_date: str     — 结束日期 "YYYY-MM-DD"
        interval: str     — K线周期 (可选, 默认 "1d")
                            可选: "1d","1wk","1mo","1h","1m"
    """
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if not data.get("ticker"):
        return jsonify({"message": "ticker is required"}), 404

    service = GlobalService()
    result = service.get_index_hist(
        ticker=data["ticker"],
        period=data.get("period", "1mo"),
        start_date=data.get("start_date"),
        end_date=data.get("end_date"),
        interval=data.get("interval", "1d"),
    )
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@global_bp.post("/index/rank")
def get_index_rank():
    """获取所有全球指数的涨跌幅排行（按 change_pct 从大到小排序）

    无 Body 参数，直接返回 14 个全球指数按涨跌幅排序后的完整行情列表。
    """
    service = GlobalService()
    result = service.get_index_rank()
    return jsonify({"code": 200, "data": result, "message": "success"}), 200
