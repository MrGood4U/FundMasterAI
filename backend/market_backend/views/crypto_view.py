from flask import Blueprint, jsonify, request

from services.crypto_service import CryptoService

crypto_bp = Blueprint("crypto", __name__, url_prefix="/api/market/crypto")


@crypto_bp.post("/books")
def get_books():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if data.get("symbol") is None:
        return jsonify({"message": "symbol is required"}), 404

    service = CryptoService()
    result = service.get_books(data.get("symbol"))
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@crypto_bp.post("/ticker")
def get_ticker():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if data.get("symbol") is None:
        return jsonify({"message": "symbol is required"}), 404

    service = CryptoService()
    result = service.get_ticker(data.get("symbol"))
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@crypto_bp.post("/klines")
def get_klines():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if data.get("symbol") is None:
        return jsonify({"message": "symbol is required"}), 404
    if data.get("start_time") is None or data.get("end_time") is None:
        return jsonify({"message": "start_time and end_time are required"}), 404

    service = CryptoService()
    result = service.get_klines(
        data.get("symbol"),
        data.get("market_type", "SPOT"),
        data.get("interval", "1m"),
        data.get("start_time"),
        data.get("end_time"),
        data.get("limit", 1000),
    )
    return jsonify({"code": 200, "data": result, "message": "success"}), 200


@crypto_bp.post("/ma")
def get_ma():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "args not found"}), 404
    if data.get("symbol") is None:
        return jsonify({"message": "symbol is required"}), 404

    service = CryptoService()
    result = service.get_ma(
        data.get("symbol"),
        data.get("market_type", "SPOT"),
        data.get("interval", "1m"),
        data.get("ma_periods"),
        data.get("start_time", 0),
        data.get("end_time", 0),
        data.get("limit", 500),
    )
    return jsonify({"code": 200, "data": result, "message": "success"}), 200
