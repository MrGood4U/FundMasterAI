from flask import Blueprint, jsonify

from services.bond_service import BondService

from flask import request

bond_bp = Blueprint("bond", __name__, url_prefix="/api/market/bond")


@bond_bp.post("/spot_quote")
def get_bond_spot_quote():
    service = BondService()
    result = service.get_bond_spot_quote()
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@bond_bp.post("/spot_deal")
def get_bond_spot_deal():
    service = BondService()
    result = service.get_bond_spot_deal()
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@bond_bp.post("/spot_quote_search")
def get_bond_spot_quote_search():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if data.get("bond_name") is None and data.get("bond_code") is None:
        return jsonify({"message": "bond_name or bond_code is required"}), 404

    service = BondService()
    result = service.get_bond_spot_quote_search(
        bond_name=data.get("bond_name"),
        bond_code=data.get("bond_code"),
    )
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@bond_bp.post("/spot_deal_search")
def get_bond_spot_deal_search():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if data.get("bond_name") is None and data.get("bond_code") is None:
        return jsonify({"message": "bond_name or bond_code is required"}), 404

    service = BondService()
    result = service.get_bond_spot_deal_search(
        bond_name=data.get("bond_name"),
        bond_code=data.get("bond_code"),
    )
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@bond_bp.post("/info_search")
def get_bond_info_search():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404

    service = BondService()
    result = service.get_bond_info_search(
        bond_name=data.get("bond_name", ""),
        bond_code=data.get("bond_code", ""),
        bond_issue=data.get("bond_issue", ""),
        bond_type=data.get("bond_type", ""),
        coupon_type=data.get("coupon_type", ""),
        issue_year=data.get("issue_year", ""),
        grade=data.get("grade", ""),
        underwriter=data.get("underwriter", ""),
    )
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@bond_bp.post("/china_yield")
def get_bond_china_yield():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if data.get("start_date") is None or data.get("end_date") is None:
        return jsonify({"message": "start_date and end_date are required"}), 404

    service = BondService()
    result, errmsg = service.get_bond_china_yield_all(
        data.get("start_date"), data.get("end_date"),
    )
    if errmsg:
        return jsonify({"code": 404, "data": [], "message": errmsg}), 404

    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@bond_bp.post("/china_yield_search")
def get_bond_china_yield_search():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if data.get("curve_name") is None:
        return jsonify({"message": "curve_name is required"}), 404
    if data.get("start_date") is None or data.get("end_date") is None:
        return jsonify({"message": "start_date and end_date are required"}), 404

    service = BondService()
    result, errmsg = service.get_bond_china_yield_search(
        data.get("curve_name"), data.get("start_date"), data.get("end_date"),
    )
    if errmsg:
        return jsonify({"code": 404, "data": [], "message": errmsg}), 404

    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@bond_bp.post("/get_name_by_code")
def get_bond_name_by_code():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if data.get("bond_code") is None:
        return jsonify({"message": "bond_code is required"}), 404

    service = BondService()
    result = service.get_bond_name_by_code(data.get("bond_code"))
    if result is None:
        return jsonify({"code": 404, "data": None, "message": "bond not found"}), 404

    return jsonify({"code": 200, "data": result, "message": "success"}), 200
