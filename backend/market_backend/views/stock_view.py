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
    