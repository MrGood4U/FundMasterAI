from flask import Flask, jsonify
from config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # --- Auto-migrate DB schema on startup ---
    from utils.schema_migration import run_migration
    run_migration()

    # --- Ensure the single SMTP config row (id=1) exists ---
    from daos.smtp_config_dao import SmtpConfigDao
    SmtpConfigDao().ensure_exists()

    # --- Ensure the single user_profile row (id=1) exists ---
    from daos.user_profile_dao import UserProfileDao
    UserProfileDao().ensure_exists()

    # Register blueprints
    from views.transaction_view import transaction_bp
    from views.holding_view import holding_bp
    from views.alert_view import alert_bp
    from views.watchlist_view import watchlist_bp
    from views.meta_view import meta_bp
    from views.allocation_view import allocation_bp
    from views.sector_view import sector_bp
    from views.fund_detail_view import fund_detail_bp
    from views.smtp_config_view import smtp_config_bp
    from views.user_profile_view import user_profile_bp

    app.register_blueprint(transaction_bp)
    app.register_blueprint(holding_bp)
    app.register_blueprint(alert_bp)
    app.register_blueprint(watchlist_bp)
    app.register_blueprint(meta_bp)
    app.register_blueprint(allocation_bp)
    app.register_blueprint(sector_bp)
    app.register_blueprint(fund_detail_bp)
    app.register_blueprint(smtp_config_bp)
    app.register_blueprint(user_profile_bp)

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
