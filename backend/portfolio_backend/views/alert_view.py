from flask import Blueprint, jsonify, request

from services.alert_service import AlertService

alert_bp = Blueprint("alert", __name__, url_prefix="/api/portfolio/alert")


@alert_bp.post("/create")
def create_alert():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 400

    service = AlertService()
    result = service.create(
        asset_type=data.get("asset_type"),
        asset_code=data.get("asset_code"),
        alert_type=data.get("alert_type"),
        trigger_mode=data.get("trigger_mode"),
        trigger_price=data.get("trigger_price"),
        trigger_pct=data.get("trigger_pct"),
        reference_trans_id=data.get("reference_trans_id"),
        notify_phone=data.get("notify_phone", False),
        notify_email=data.get("notify_email", False),
        notes=data.get("notes"),
    )
    if "error" in result:
        return jsonify({"code": 400, "message": result["error"]}), 400
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@alert_bp.get("/<int:alert_id>")
def get_alert(alert_id):
    service = AlertService()
    result = service.get_by_id(alert_id)
    if not result:
        return jsonify({"code": 404, "message": "not found"}), 404
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@alert_bp.post("/update")
def update_alert():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 400

    alert_id = data.get("alert_id")
    if alert_id is None:
        return jsonify({"message": "alert_id is required"}), 400

    service = AlertService()
    ok = service.update(alert_id,
                        alert_type=data.get("alert_type"),
                        trigger_mode=data.get("trigger_mode"),
                        trigger_price=data.get("trigger_price"),
                        trigger_pct=data.get("trigger_pct"),
                        reference_trans_id=data.get("reference_trans_id"),
                        notify_phone=data.get("notify_phone"),
                        notify_email=data.get("notify_email"),
                        is_enabled=data.get("is_enabled"),
                        notes=data.get("notes"))
    if not ok:
        return jsonify({"code": 404, "message": "not found or no fields to update"}), 404
    return jsonify({"code": 200, "message": "success"}), 200


@alert_bp.post("/delete")
def delete_alert():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 400

    alert_id = data.get("alert_id")
    if alert_id is None:
        return jsonify({"message": "alert_id is required"}), 400

    service = AlertService()
    ok = service.delete(alert_id)
    if not ok:
        return jsonify({"code": 404, "message": "not found"}), 404
    return jsonify({"code": 200, "message": "success"}), 200


@alert_bp.get("/list")
def list_alerts():
    is_enabled_raw = request.args.get("is_enabled")
    is_enabled = None
    if is_enabled_raw is not None:
        is_enabled = is_enabled_raw.lower() in ("1", "true", "yes")

    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)

    service = AlertService()
    result = service.list_by_user(
        is_enabled=is_enabled,
        asset_type=request.args.get("asset_type"),
        page=page,
        page_size=page_size,
    )
    return jsonify({"code": 200, "data": result, "message": "success"}), 200
