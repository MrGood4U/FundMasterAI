from flask import Blueprint, jsonify

from services.public_fund_service import PublicFundService

from flask import request

from datetime import datetime

public_fund_bp = Blueprint("public_fund", __name__, url_prefix="/api/market/fund_public")

def validate_date(date_str):
    try:
        datetime.strptime(date_str, "%Y%m%d")
        return True
    except ValueError:
        return False

@public_fund_bp.post("/real_time_get_one")
def get_one_real_time():
    data = request.get_json()
    if data is None:
        return jsonify({"code": 404, "message": "args not found"}), 404
    if data.get("platform") is None or data.get("symbol") is None:
        return jsonify({"code": 404, "message": "args not found"}), 404
    if data.get("name") is None and data.get("code") is None:
        return jsonify({"code": 404, "message": "args not found"}), 404

    service = PublicFundService()
    result, errmsg = service.get_one_real_time(data.get("name"), data.get("code"), data.get("platform"), data.get("symbol"))

    if errmsg:
        return jsonify({"code": 404, "data": [], "message": errmsg}), 404

    return jsonify({"code": 200, "data": result, "message": "success"}), 200

@public_fund_bp.post("/real_time_get_all")
def get_all_real_time():
    data = request.get_json()
    if data is None:
        return jsonify({"code": 404, "message": "args not found"}), 404
    if data.get("platform") is None or data.get("symbol") is None:
        return jsonify({"code": 404, "message": "args not found"}), 404

    service = PublicFundService()
    result = service.get_all_real_time(data.get("platform"), data.get("symbol"))

    return jsonify({"code": 200, "data": result, "message": "success"}), 200

@public_fund_bp.post("/hist")
def get_public_fund_hist():
    data = request.get_json()
    if data is None:
        return jsonify({"code": 404, "message": "args not found"}), 404
    if data.get("platform") is None or data.get("symbol") is None:
        return jsonify({"code": 404, "message": "args not found"}), 404
    service = PublicFundService()
    result = service.get_hist(data.get("symbol"), data.get("platform"), data.get("code"), data.get("start_date"), data.get("end_date"), data.get("period"), data.get("adjust"))
    
    return jsonify({"code": 200, "data": result, "message": "success"}), 200

@public_fund_bp.post("/hist_min")
def get_public_fund_hist_min():
    data = request.get_json()
    if data is None:
        return jsonify({"code": 404, "message": "args not found"}), 404
    if data.get("platform") is None or data.get("code") is None:
        return jsonify({"code": 404, "message": "args not found"}), 404
    service = PublicFundService()
    result = service.get_hist_min(data.get("symbol"), data.get("platform"), data.get("code"), data.get("start_date"), data.get("end_date"), data.get("period"), data.get("adjust"))
    
    return jsonify({"code": 200, "data": result, "message": "success"}), 200

@public_fund_bp.get("/fund_name_list")
def get_public_fund_name_list():
    service = PublicFundService()
    result = service.get_fund_name_list()
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@public_fund_bp.post("/batch_spot")
def get_batch_fund_spot():
    data = request.get_json()
    if data is None:
        return jsonify({"code": 404, "message": "args not found"}), 404
    if data.get("codes") is None or len(data["codes"]) == 0:
        return jsonify({"code": 404, "message": "codes is required"}), 404
    if data.get("platform") is None or data.get("symbol") is None:
        return jsonify({"code": 404, "message": "args not found"}), 404

    service = PublicFundService()
    all_data = service.get_all_real_time(data.get("platform"), data.get("symbol"))
    if all_data is None:
        return jsonify({"code": 200, "data": [], "message": "success"}), 200

    code_set = set(data["codes"])
    result = [item for item in all_data
              if item.get("fund_code") in code_set
              or item.get("code") in code_set]
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@public_fund_bp.post("/portfolio_holds")
def get_portfolio_holds():
    data = request.get_json()
    if data is None:
        return jsonify({"code": 404, "message": "args not found"}), 404
    if data.get("code") is None:
        return jsonify({"code": 404, "message": "code is required"}), 404

    service = PublicFundService()
    result = service.get_fund_portfolio_holds(
        code=data.get("code"),
        year=data.get("year", str(datetime.now().year)),
    )
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@public_fund_bp.post("/individual_analysis")
def get_individual_analysis():
    data = request.get_json()
    if data is None:
        return jsonify({"code": 404, "message": "args not found"}), 404
    if data.get("code") is None:
        return jsonify({"code": 404, "message": "code is required"}), 404

    service = PublicFundService()
    result = service.get_fund_individual_analysis(data.get("code"))
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@public_fund_bp.post("/profit_probability")
def get_profit_probability():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if data.get("code") is None:
        return jsonify({"message": "code is required"}), 404

    service = PublicFundService()
    result = service.get_fund_individual_profit_probability(data.get("code"))
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@public_fund_bp.post("/value_estimation")
def get_value_estimation():
    data = request.get_json()
    if data is None:
        return jsonify({"code": 404, "message": "args not found"}), 404
    if data.get("code") is None:
        return jsonify({"code": 404, "message": "code is required"}), 404

    service = PublicFundService()
    result = service.get_fund_value_estimation(data.get("code"), data.get("fund_type", "all"))
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@public_fund_bp.post("/value_estimation_list")
def get_value_estimation_list():
    data = request.get_json()

    service = PublicFundService()
    result = service.get_fund_value_estimation_list(data.get("fund_type", "all"))
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@public_fund_bp.post("/rank")
def get_fund_rank():
    data = request.get_json()
    if data is None:
        return jsonify({"code": 404, "message": "args not found"}), 404

    service = PublicFundService()
    result = service.fund_open_fund_rank(
        fund_type=data.get("fund_type", "all"),
    )
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@public_fund_bp.post("/info_index")
def get_info_index():
    data = request.get_json()
    if data is None:
        return jsonify({"code": 404, "message": "args not found"}), 404

    service = PublicFundService()
    result = service.get_fund_info_index(
        symbol=data.get("symbol", "all"),
        indicator=data.get("indicator", "all"),
    )
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@public_fund_bp.post("/hist_kline")
def get_public_fund_hist_kline():
    data = request.get_json()
    if data is None:
        return jsonify({"code": 404, "message": "args not found"}), 404
    if data.get("platform") is None or data.get("symbol") is None:
        return jsonify({"code": 404, "message": "args not found"}), 404
    service = PublicFundService()
    result = service.get_hist_kline(
        data.get("symbol"), data.get("platform"), data.get("code"),
        data.get("start_date"), data.get("end_date"),
        data.get("period"), data.get("adjust"),
    )
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@public_fund_bp.post("/hist_min_kline")
def get_public_fund_hist_min_kline():
    data = request.get_json()
    if data is None:
        return jsonify({"code": 404, "message": "args not found"}), 404
    if data.get("platform") is None or data.get("code") is None:
        return jsonify({"code": 404, "message": "args not found"}), 404
    service = PublicFundService()
    result = service.get_hist_min_kline(
        data.get("symbol"), data.get("platform"), data.get("code"),
        data.get("start_date"), data.get("end_date"),
        data.get("period"), data.get("adjust"),
    )
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@public_fund_bp.post("/individual_basic_info")
def get_individual_basic_info():
    data = request.get_json()
    if data is None:
        return jsonify({"code": 404, "message": "args not found"}), 404
    if data.get("code") is None:
        return jsonify({"code": 404, "message": "code is required"}), 404

    service = PublicFundService()
    result = service.get_fund_individual_basic_info(data.get("code"))
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@public_fund_bp.post("/individual_detail_hold")
def get_individual_detail_hold():
    data = request.get_json()
    if data is None:
        return jsonify({"code": 404, "message": "args not found"}), 404
    if data.get("code") is None:
        return jsonify({"code": 404, "message": "code is required"}), 404

    # date 8位数字, 不填的话应该改为默认今天的日期
    service = PublicFundService()
    result = service.get_fund_individual_detail_hold(
        code=data.get("code"),
        date=data.get("date", datetime.now().strftime("%Y%m%d"))
    )
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@public_fund_bp.post("/portfolio_industry_allocation")
def get_portfolio_industry_allocation():
    data = request.get_json()
    if data is None:
        return jsonify({"code": 404, "message": "args not found"}), 404
    if data.get("code") is None:
        return jsonify({"code": 404, "message": "code is required"}), 404

    service = PublicFundService()
    result = service.get_fund_portfolio_industry_allocation_em(
        code=data.get("code"),
        year=data.get("year", str(datetime.now().year)),
    )
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@public_fund_bp.post("/portfolio_hold_stock")
def get_portfolio_hold_stock():
    data = request.get_json()
    if data is None:
        return jsonify({"code": 404, "message": "args not found"}), 404
    if data.get("code") is None:
        return jsonify({"code": 404, "message": "code is required"}), 404

    service = PublicFundService()
    result = service.get_fund_portfolio_hold_stock(
        code=data.get("code"),
        year=data.get("year", str(datetime.now().year)),
    )
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@public_fund_bp.post("/portfolio_hold_bond")
def get_portfolio_hold_bond():
    data = request.get_json()
    if data is None:
        return jsonify({"code": 404, "message": "args not found"}), 404
    if data.get("code") is None:
        return jsonify({"code": 404, "message": "code is required"}), 404

    service = PublicFundService()
    result = service.get_fund_portfolio_hold_bond(
        code=data.get("code"),
        year=data.get("year", str(datetime.now().year)),
    )
    return jsonify({"code": 200, "data": result, "message": "success"}), 200