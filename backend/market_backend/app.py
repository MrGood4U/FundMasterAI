
import sys

# Monkey-patch: yfinance depends on sqlite3 (via multitasking), but this
# Python was built without _sqlite3.  Use the pure-Python pysqlite3 instead.
import pysqlite3

sys.modules["sqlite3"] = pysqlite3

from flask import Flask, jsonify
from flask_openapi3 import OpenAPI, Info
from config import Config
from daos.cache_dao import CacheDao
from utils.cache_scheduler import CacheScheduler
import atexit
import os


# module-level singleton so the scheduler lifecycle is tied to the process
_scheduler: CacheScheduler | None = None


def create_app():
    info = Info(title="market backend API document", version="1.0.0")
    app = OpenAPI(
        __name__,
        info=info
    )
    # app = Flask(__name__)
    app.config.from_object(Config)

    # ---- cache layer ---------------------------------------------------
    cache_dao = CacheDao.from_config()
    app.config["cache_dao"] = cache_dao

    # Skip scheduler during test runs to avoid polluting test data.
    if not os.environ.get("MARKET_TESTING"):
        global _scheduler
        _scheduler = CacheScheduler(cache_dao)
        _scheduler.start()
        atexit.register(_scheduler.stop)

    # ---- blueprints ----------------------------------------------------
    from views.public_fund_view import public_fund_bp
    from views.stock_view import stock_bp
    from views.crypto_view import crypto_bp
    from views.meta_view import meta_bp
    from views.bond_view import bond_bp
    from views.global_view import global_bp
    from views.macro_view import macro_bp

    app.register_blueprint(public_fund_bp)
    app.register_blueprint(stock_bp)
    app.register_blueprint(crypto_bp)
    app.register_blueprint(meta_bp)
    app.register_blueprint(bond_bp)
    app.register_blueprint(global_bp)
    app.register_blueprint(macro_bp)

    @app.route('/')
    def hello_world():
        return jsonify(message="Hello from FundMasterAI Market Backend!")

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(port=app.config["HTTP_PORT"], debug=True)
