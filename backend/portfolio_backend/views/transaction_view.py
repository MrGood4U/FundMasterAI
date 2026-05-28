from flask import Blueprint, jsonify, request

from services.transaction_service import TransactionService

transaction_bp = Blueprint("transaction", __name__, url_prefix="/api/portfolio/transaction")


@transaction_bp.post("/create")
def create_transaction():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 400

    service = TransactionService()
    result = service.create(
        asset_type=data.get("asset_type"),
        asset_code=data.get("asset_code"),
        asset_name=data.get("asset_name"),
        trans_type=data.get("trans_type"),
        price=data.get("price"),
        quantity=data.get("quantity"),
        fee=data.get("fee", 0),
        trans_date=data.get("trans_date"),
        portfolio_tag=data.get("portfolio_tag"),
        notes=data.get("notes"),
    )
    if "error" in result:
        return jsonify({"code": 400, "message": result["error"]}), 400
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@transaction_bp.get("/<int:trans_id>")
def get_transaction(trans_id):
    service = TransactionService()
    result = service.get_by_id(trans_id)
    if not result:
        return jsonify({"code": 404, "message": "not found"}), 404
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@transaction_bp.post("/update")
def update_transaction():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 400

    trans_id = data.get("trans_id")
    if trans_id is None:
        return jsonify({"message": "trans_id is required"}), 400

    service = TransactionService()
    ok = service.update(trans_id,
                        asset_name=data.get("asset_name"),
                        price=data.get("price"),
                        quantity=data.get("quantity"),
                        fee=data.get("fee"),
                        trans_date=data.get("trans_date"),
                        portfolio_tag=data.get("portfolio_tag"),
                        notes=data.get("notes"))
    if not ok:
        return jsonify({"code": 404, "message": "not found or no fields to update"}), 404
    return jsonify({"code": 200, "message": "success"}), 200


@transaction_bp.post("/delete")
def delete_transaction():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 400

    trans_id = data.get("trans_id")
    if trans_id is None:
        return jsonify({"message": "trans_id is required"}), 400

    service = TransactionService()
    ok = service.delete(trans_id)
    if not ok:
        return jsonify({"code": 404, "message": "not found"}), 404
    return jsonify({"code": 200, "message": "success"}), 200


@transaction_bp.get("/list")
def list_transactions():
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)

    service = TransactionService()
    result = service.list_by_user(
        asset_type=request.args.get("asset_type"),
        asset_code=request.args.get("asset_code"),
        trans_type=request.args.get("trans_type"),
        start_date=request.args.get("start_date"),
        end_date=request.args.get("end_date"),
        page=page,
        page_size=page_size,
    )
    return jsonify({"code": 200, "data": result, "message": "success"}), 200
