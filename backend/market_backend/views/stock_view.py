from flask import Blueprint, jsonify

from services.stock_service import StockService

from flask import request

stock_bp = Blueprint("stock", __name__, url_prefix="/api/market/stock")

@stock_bp.post("/a/one_spot")
def get_a_spot():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if data.get("platform") is None:
        return jsonify({"message": "args not found"}), 404
    service = StockService()
    result = service.get_a_spot(data.get("platform"), data.get("code"), data.get("name"))
    return jsonify({"code": 200, "data": result, "message": "success"}), 200

@stock_bp.post("/a/all_spot")
def get_all_a_spot():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if data.get("platform") is None:
        return jsonify({"message": "args not found"}), 404
    service = StockService()
    result = service.get_all_a_spot(data.get("platform"))
    return jsonify({"code": 200, "data": result, "message": "success"}), 200

@stock_bp.post("/a/hist")
def get_a_hist():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if data.get("platform") is None or data.get("code") is None:
        return jsonify({"message": "args not found"}), 404
    service = StockService()
    result = service.get_a_hist(data.get("platform"), data.get("code"), data.get("period"), data.get("start_date"), 
                                data.get("end_date"), data.get("adjust"))
    return jsonify({"code": 200, "data": result, "message": "success"}), 200

@stock_bp.post("/a/bid_ask")
def get_a_bid_ask():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if data.get("code") is None:
        return jsonify({"message": "args not found"}), 404
    service = StockService()
    result = service.get_a_bid_ask(data.get("platform"), data.get("code"))
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@stock_bp.post("/a/batch_spot")
def get_batch_a_spot():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if data.get("codes") is None or len(data["codes"]) == 0:
        return jsonify({"message": "codes is required"}), 404

    service = StockService()
    all_data = service.get_all_a_spot(data.get("platform", "eastmoney"))
    if all_data is None:
        return jsonify({"code": 200, "data": [], "message": "success"}), 200

    code_set = set(data["codes"])
    result = [item for item in all_data
              if item.get("stock_code") in code_set
              or item.get("code") in code_set]
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@stock_bp.post("/a/hist_kline")
def get_a_hist_kline():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if data.get("platform") is None or data.get("code") is None:
        return jsonify({"message": "args not found"}), 404
    service = StockService()
    result = service.get_a_hist_kline(
        data.get("platform"), data.get("code"), data.get("period"),
        data.get("start_date"), data.get("end_date"), data.get("adjust"),
    )
    return jsonify({"code": 200, "data": result, "message": "success"}), 200