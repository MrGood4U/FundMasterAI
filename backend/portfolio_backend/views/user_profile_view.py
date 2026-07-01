from flask import Blueprint, jsonify, request

from services.user_profile_service import UserProfileService

user_profile_bp = Blueprint("user_profile", __name__, url_prefix="/api/portfolio/user_profile")

# ── 单用户系统：只维护 id=1 的一条用户信息 ──


@user_profile_bp.get("/get_profile")
def get_user_profile():
    """获取用户个人信息（仅有一条，id=1）。"""
    service = UserProfileService()
    profile = service.get_profile()
    if not profile:
        return jsonify({"code": 404, "message": "not found"}), 404
    return jsonify({"code": 200, "data": profile, "message": "success"}), 200


@user_profile_bp.post("/update_phone")
def update_phone():
    """更新手机号（始终更新 id=1）。"""
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 400

    phone = data.get("phone")
    if not phone:
        return jsonify({"code": 400, "message": "phone is required"}), 400

    service = UserProfileService()
    ok = service.update_phone(phone)
    if not ok:
        return jsonify({"code": 400, "message": "invalid phone number"}), 400
    return jsonify({"code": 200, "message": "success"}), 200


@user_profile_bp.post("/update_email")
def update_email():
    """更新邮箱（始终更新 id=1）。"""
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 400

    email = data.get("email")
    if not email:
        return jsonify({"code": 400, "message": "email is required"}), 400

    service = UserProfileService()
    ok = service.update_email(email)
    if not ok:
        return jsonify({"code": 400, "message": "invalid email"}), 400
    return jsonify({"code": 200, "message": "success"}), 200


@user_profile_bp.post("/update")
def update_user_profile():
    """更新用户个人信息（始终更新 id=1）。"""
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 400

    phone = data.get("phone")
    email = data.get("email")

    if not phone and not email:
        return jsonify({"code": 400, "message": "phone or email is required"}), 400

    service = UserProfileService()
    ok = service.update(phone=phone, email=email)
    if not ok:
        return jsonify({"code": 400, "message": "invalid fields"}), 400
    return jsonify({"code": 200, "message": "success"}), 200
