from flask import Blueprint, jsonify, request

from services.fund_detail_service import FundDetailService

fund_detail_bp = Blueprint("fund_detail", __name__, url_prefix="/api/portfolio/fund")


@fund_detail_bp.post("/detail_hold")
def get_detail_hold():
    """资产配置：查询基金在某时点的股票/债券/现金等资产占比。

    body: {"code": "000001", "date": "20241231"}  // date 可选，默认今天
    """
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 400
    if data.get("code") is None:
        return jsonify({"message": "code is required"}), 400

    service = FundDetailService()
    result = service.get_detail_hold(code=data["code"], date=data.get("date"))
    if result is None:
        return jsonify({"code": 404, "data": None, "message": "not found"}), 404
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@fund_detail_bp.post("/industry_allocation")
def get_industry_allocation():
    """行业配置：查询基金某个年度的行业持仓分布。

    body: {"code": "000001", "year": "2025"}  // year 可选，默认当前年份
    """
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 400
    if data.get("code") is None:
        return jsonify({"message": "code is required"}), 400

    service = FundDetailService()
    result = service.get_industry_allocation(code=data["code"], year=data.get("year"))
    if result is None:
        return jsonify({"code": 404, "data": None, "message": "not found"}), 404
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@fund_detail_bp.post("/stock_holds")
def get_stock_holds():
    """股票持仓：查询基金某个年度的全部股票持仓明细。

    body: {"code": "000001", "year": "2025"}  // year 可选，默认当前年份
    """
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 400
    if data.get("code") is None:
        return jsonify({"message": "code is required"}), 400

    service = FundDetailService()
    result = service.get_stock_holds(code=data["code"], year=data.get("year"))
    if result is None:
        return jsonify({"code": 404, "data": None, "message": "not found"}), 404
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@fund_detail_bp.post("/bond_holds")
def get_bond_holds():
    """债券持仓：查询基金某个年度的全部债券持仓明细。

    body: {"code": "000001", "year": "2025"}  // year 可选，默认当前年份
    """
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 400
    if data.get("code") is None:
        return jsonify({"message": "code is required"}), 400

    service = FundDetailService()
    result = service.get_bond_holds(code=data["code"], year=data.get("year"))
    if result is None:
        return jsonify({"code": 404, "data": None, "message": "not found"}), 404
    return jsonify({"code": 200, "data": result, "message": "success"}), 200
