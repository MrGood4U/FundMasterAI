from flask import Blueprint, jsonify

from services.example_service import ExampleService

example_bp = Blueprint("example", __name__, url_prefix="/api/examples")


@example_bp.get("/<int:example_id>")
def get_example(example_id: int):
    data = ExampleService().get_example_detail(example_id)
    if data is None:
        return jsonify({"message": "Example not found", "example_id": example_id}), 404

    return jsonify(data), 200
