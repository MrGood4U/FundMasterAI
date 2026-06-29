from flask import Blueprint, jsonify, request

from services.watchlist_service import WatchlistService

watchlist_bp = Blueprint("watchlist", __name__, url_prefix="/api/portfolio/watchlist")


@watchlist_bp.post("/create")
def add_to_watchlist():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 400

    service = WatchlistService()
    result = service.add(
        asset_type=data.get("asset_type"),
        asset_code=data.get("asset_code"),
        asset_name=data.get("asset_name"),
        target_price=data.get("target_price"),
        priority=data.get("priority", 0),
        notes=data.get("notes"),
    )
    if "error" in result:
        return jsonify({"code": 400, "message": result["error"]}), 400
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@watchlist_bp.post("/delete")
def remove_from_watchlist():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 400

    watchlist_id = data.get("watchlist_id")
    if watchlist_id is None:
        return jsonify({"message": "watchlist_id is required"}), 400

    service = WatchlistService()
    ok = service.remove(watchlist_id)
    if not ok:
        return jsonify({"code": 404, "message": "not found"}), 404
    return jsonify({"code": 200, "message": "success"}), 200


@watchlist_bp.get("/list")
def list_watchlist():
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)

    service = WatchlistService()
    result = service.list_by_user(
        asset_type=request.args.get("asset_type"),
        page=page,
        page_size=page_size,
    )
    return jsonify({"code": 200, "data": result, "message": "success"}), 200
