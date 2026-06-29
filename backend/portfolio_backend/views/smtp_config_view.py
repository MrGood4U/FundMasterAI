from flask import Blueprint, jsonify, request

from services.smtp_config_service import SmtpConfigService

smtp_config_bp = Blueprint("smtp_config", __name__, url_prefix="/api/portfolio/smtp_config")

# ── 单用户系统：只维护 id=1 的一条 SMTP 配置，仅支持读取和更新 ──


@smtp_config_bp.get("/get_config")
def get_smtp_config():
    """获取 SMTP 配置（仅有一条，id=1）。"""
    service = SmtpConfigService()
    config = service.get_config()
    if not config:
        return jsonify({"code": 404, "message": "not found"}), 404
    config["password"] = "******"
    return jsonify({"code": 200, "data": config, "message": "success"}), 200


@smtp_config_bp.post("/update_config")
def update_smtp_config():
    """更新 SMTP 配置（始终更新 id=1）。"""
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 400

    service = SmtpConfigService()
    ok = service.update(
        email=data.get("email"),
        sender_name=data.get("sender_name"),
        smtp_host=data.get("smtp_host"),
        smtp_port=data.get("smtp_port"),
        password=data.get("password"),
        encryption=data.get("encryption"),
    )
    if not ok:
        return jsonify({"code": 400, "message": "invalid fields or not found"}), 400
    return jsonify({"code": 200, "message": "success"}), 200


@smtp_config_bp.post("/test_email")
def test_smtp_config_email():
    """使用当前 SMTP 配置发送测试邮件。"""
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 400

    to_email = data.get("to_email")
    if to_email is None:
        return jsonify({"message": "to_email is required"}), 400

    service = SmtpConfigService()
    result = service.test_email(to_email)
    if "error" in result:
        return jsonify({"code": 400, "message": result["error"]}), 400
    return jsonify({"code": 200, "message": result["message"]}), 200
