from flask import Blueprint, jsonify

from services.sector_service import SectorService

sector_bp = Blueprint("sector", __name__, url_prefix="/api/portfolio/sector")


@sector_bp.get("/exposure")
def get_sector_exposure():
    """穿透持仓汇总各行业的市值分布。"""
    service = SectorService()
    result = service.get_sector_exposure()
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@sector_bp.get("/concentration")
def get_sector_concentration():
    """集中度分析：Top3行业、Top5个股、风险标记。"""
    service = SectorService()
    result = service.get_sector_concentration()
    return jsonify({"code": 200, "data": result, "message": "success"}), 200
