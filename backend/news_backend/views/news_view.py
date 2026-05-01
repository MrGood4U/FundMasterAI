from flask import Blueprint, jsonify
from services.news_service import NewsService
from flask import request

news_bp = Blueprint("news", __name__, url_prefix="/api/news")


@news_bp.post("/stock/get_recent_news")
def get_stock_recent_news():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if data.get("symbol") is None:
        return jsonify({"message": "args not found"}), 404
    service = NewsService()
    result = service.get_stock_recent_news(data.get("symbol"))
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@news_bp.post("/public_fund/get_announcement")
def get_public_fund_announcement():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if data.get("code") is None:
        return jsonify({"message": "args not found"}), 404
    service = NewsService()
    result = service.get_public_fund_announcement(data.get("code"))
    return jsonify({"code": 200, "data": result, "message": "success"}), 200