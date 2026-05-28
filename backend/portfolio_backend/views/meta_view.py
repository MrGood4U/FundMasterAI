from flask import Blueprint, jsonify, request

from utils.function_registry import get_all_functions, get_functions_by_tag

meta_bp = Blueprint("meta", __name__, url_prefix="/api/portfolio")


@meta_bp.get("/functions")
def list_functions():
    """返回所有可用接口的 Function Calling 定义，供 LLM agent 自行发现和调用。

    可选查询参数:
        tag: transaction / holding / alert / watchlist  按类别筛选
    """
    tag = request.args.get("tag")
    if tag:
        funcs = get_functions_by_tag(tag)
    else:
        funcs = get_all_functions()
    return jsonify({"code": 200, "data": funcs, "message": "success"}), 200
