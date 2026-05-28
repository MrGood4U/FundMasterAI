from flask import Blueprint, jsonify, request

from services.holding_service import HoldingService

holding_bp = Blueprint("holding", __name__, url_prefix="/api/portfolio/holding")


@holding_bp.get("/list")
def list_holdings():
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)

    service = HoldingService()
    result = service.get_holdings(
        asset_type=request.args.get("asset_type"),
        page=page,
        page_size=page_size,
    )
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@holding_bp.get("/detail")
def get_holding_detail():
    asset_type = request.args.get("asset_type")
    asset_code = request.args.get("asset_code")

    if asset_type is None or asset_code is None:
        return jsonify({"message": "asset_type and asset_code are required"}), 400

    service = HoldingService()
    result = service.get_holding_detail(asset_type, asset_code)
    if result is None:
        return jsonify({"code": 404, "message": "holding not found"}), 404
    return jsonify({"code": 200, "data": result, "message": "success"}), 200
