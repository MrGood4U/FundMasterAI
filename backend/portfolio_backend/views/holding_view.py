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


@holding_bp.post("/create")
def create_holding():
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"code": 400, "message": "request body is required"}), 400

    required_fields = ["asset_type", "asset_code", "asset_name",
                       "trans_type", "price", "quantity", "fee", "trans_date"]
    for field in required_fields:
        if field not in body or body[field] is None:
            return jsonify({"code": 400, "message": f"{field} is required"}), 400

    if body["trans_type"] not in ("buy", "sell"):
        return jsonify({"code": 400, "message": "trans_type must be buy or sell"}), 400

    service = HoldingService()
    trans_id = service.create_holding(
        asset_type=body["asset_type"],
        asset_code=body["asset_code"],
        asset_name=body["asset_name"],
        trans_type=body["trans_type"],
        price=float(body["price"]),
        quantity=float(body["quantity"]),
        fee=float(body.get("fee", 0)),
        trans_date=body["trans_date"],
        portfolio_tag=body.get("portfolio_tag"),
        notes=body.get("notes"),
    )
    return jsonify({"code": 200, "data": {"id": trans_id}, "message": "success"}), 200


@holding_bp.post("/delete")
def delete_holding():
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"code": 400, "message": "request body is required"}), 400

    trans_id = body.get("id")
    asset_type = body.get("asset_type")
    asset_code = body.get("asset_code")

    if not trans_id and not (asset_type and asset_code):
        return jsonify({
            "code": 400,
            "message": "provide either id (transaction id) or asset_type + asset_code"
        }), 400

    service = HoldingService()
    deleted = service.delete_holding(
        trans_id=trans_id,
        asset_type=asset_type,
        asset_code=asset_code,
    )
    if deleted == 0:
        return jsonify({"code": 404, "message": "no records found to delete"}), 404
    return jsonify({"code": 200, "data": {"deleted": deleted}, "message": "success"}), 200
