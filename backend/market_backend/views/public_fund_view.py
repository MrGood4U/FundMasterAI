from flask import Blueprint, jsonify

from services.public_fund_service import PublicFundService

from flask import request

public_fund_bp = Blueprint("public_fund", __name__, url_prefix="/api/market/fund_public")

@public_fund_bp.post("/real_time_get_one")
def get_one_real_time():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if data.get("platform") is None or data.get("symbol") is None:
        return jsonify({"message": "args not found"}), 404
    if data.get("name") is None and data.get("code") is None:
        return jsonify({"message": "args not found"}), 404

    service = PublicFundService()
    result = service.get_public_fund_one_real_time(data.get("name"), data.get("code"), data.get("platform"), data.get("symbol"))

    return jsonify({"code": 200, "data": result, "message": "success"}), 200

@public_fund_bp.post("/real_time_get_all")
def get_all_real_time():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if data.get("platform") is None or data.get("symbol") is None:
        return jsonify({"message": "args not found"}), 404

    service = PublicFundService()
    result = service.get_public_fund_all_real_time(data.get("platform"), data.get("symbol"))

    return jsonify({"code": 200, "data": result, "message": "success"}), 200

@public_fund_bp.post("/hist")
def get_public_fund_hist():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if data.get("platform") is None or data.get("symbol") is None:
        return jsonify({"message": "args not found"}), 404
    service = PublicFundService()
    result = service.get_public_fund_hist(data.get("symbol"), data.get("platform"), data.get("code"), data.get("start_date"), data.get("end_date"), date.get("period"), data.get("adjust"))
    
    return jsonify({"code": 200, "data": result, "message": "success"}), 200

@public_fund_bp.post("/hist_min")
def get_public_fund_hist_min():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if data.get("platform") is None or data.get("symbol") is None:
        return jsonify({"message": "args not found"}), 404
    service = PublicFundService()
    result = service.get_public_fund_hist_min(data.get("symbol"), data.get("platform"), data.get("code"), data.get("start_date"), data.get("end_date"), date.get("period"), data.get("adjust"))
    
    return jsonify({"code": 200, "data": result, "message": "success"}), 200
