from flask import Blueprint, jsonify, request

from services.allocation_service import AllocationService

allocation_bp = Blueprint("allocation", __name__, url_prefix="/api/portfolio/allocation")


@allocation_bp.get("/current")
def get_current_allocation():
    """获取当前各类资产持仓占比（基于实时市值）。"""
    service = AllocationService()
    result = service.get_current_allocation()
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@allocation_bp.post("/target")
def set_target_allocation():
    """设定目标配置。body: {"stock": 40, "fund": 30, "bond": 20, "crypto": 10}"""
    data = request.get_json()
    if data is None:
        return jsonify({"code": 400, "message": "args not found"}), 400

    service = AllocationService()
    result = service.set_target_allocation(data)
    if "error" in result:
        return jsonify({"code": 400, "message": result["error"]}), 400
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@allocation_bp.get("/target")
def get_target_allocation():
    """读取已保存的目标配置。"""
    service = AllocationService()
    result = service.get_target_allocation()
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@allocation_bp.get("/drift")
def get_allocation_drift():
    """计算当前配置与目标配置的偏离度。"""
    service = AllocationService()
    result = service.get_drift()
    return jsonify({"code": 200, "data": result, "message": "success"}), 200
