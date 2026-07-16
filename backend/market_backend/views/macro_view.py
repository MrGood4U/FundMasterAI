from flask import Blueprint, jsonify, request

from services.macro_service import MacroService

macro_bp = Blueprint("macro", __name__, url_prefix="/api/market/macro")


# ==================================================================
# 元信息接口 —— 让前端知道有哪些国家、指标、字段
# ==================================================================

@macro_bp.post("/countries")
def get_countries():
    """获取支持的宏观经济国家/地区列表

    Response:
        {code, data: [{country, indicator_count}, ...]}
    """
    service = MacroService()
    result = service.get_supported_countries()
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@macro_bp.post("/indicators")
def get_indicators():
    """获取指定国家（或全部）的宏观指标列表

    Body:
        country: str, optional — 国家代码，如 "china"。不传则返回全部国家。

    Response:
        {code, data: {china: [{indicator, name, desc, column_count, extra_params}, ...]}}
    """
    data = request.get_json()
    country = data.get("country") if data else None

    service = MacroService()
    result = service.get_indicator_list(country)
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@macro_bp.post("/schema")
def get_schema():
    """获取指定指标的完整 Schema（含输出字段定义）

    前端可通过此接口了解：
    - 该指标有哪些输出列
    - 每列的中文名和含义
    - 有哪些可传递的额外参数

    Body:
        country:   str  — 国家代码，如 "china"
        indicator: str  — 指标 key，如 "cpi"

    Response:
        {code, data: {country, indicator, name, desc, extra_params, columns: {key: {name, desc}}}}
    """
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if not data.get("country") or not data.get("indicator"):
        return jsonify({"message": "country and indicator are required"}), 404

    service = MacroService()
    result = service.get_indicator_schema(data["country"], data["indicator"])
    if result is None:
        return jsonify({"code": 404, "data": None,
                        "message": f"indicator not found: {data.get('country')}/{data.get('indicator')}"}), 404
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


# ==================================================================
# 数据查询接口
# ==================================================================

@macro_bp.post("/data")
def get_macro_data():
    """获取宏观数据

    Body:
        country:   str            — 国家代码，如 "china"
        indicator: str            — 指标 key，如 "cpi"
        extra:    dict, optional  — 额外参数，如 {"city_first": "深圳", "city_second": "广州"}
                                    （具体支持哪些参数见 /macro/schema 返回的 extra_params）

    Response:
        {code, data: [{column: value, ...}, ...]}
    """
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if not data.get("country") or not data.get("indicator"):
        return jsonify({"message": "country and indicator are required"}), 404

    service = MacroService()
    # 透传前端给的 extra 参数
    extra = data.get("extra", {}) or {}
    result = service.get_macro_data(
        country=data["country"],
        indicator=data["indicator"],
        **extra,
    )
    if not result:
        return jsonify({"code": 500, "data": [],
                        "message": f"failed to fetch macro data: {data.get('country')}/{data.get('indicator')}"}), 500
    return jsonify({"code": 200, "data": result, "message": "success"}), 200
