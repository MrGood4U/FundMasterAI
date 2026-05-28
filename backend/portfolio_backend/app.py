from flask import Flask, jsonify
from config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register blueprints
    from views.transaction_view import transaction_bp
    from views.holding_view import holding_bp
    from views.alert_view import alert_bp
    from views.watchlist_view import watchlist_bp
    from views.meta_view import meta_bp

    app.register_blueprint(transaction_bp)
    app.register_blueprint(holding_bp)
    app.register_blueprint(alert_bp)
    app.register_blueprint(watchlist_bp)
    app.register_blueprint(meta_bp)

    @app.route("/")
    def hello_world():
        return jsonify(message="Hello from FundMasterAI Portfolio Backend!")

    if not app.config.get("TESTING"):
        from alert_checker import start_alert_checker
        start_alert_checker(app)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(port=app.config["HTTP_PORT"], debug=True)
