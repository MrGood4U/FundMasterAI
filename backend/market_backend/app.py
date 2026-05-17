
from pathlib import Path

from flask import Flask, jsonify, redirect, send_from_directory
from flask_openapi3 import OpenAPI, Info
from config import Config

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend_new"

def create_app():
    info = Info(title="market backend API document", version="1.0.0")
    app = OpenAPI(
        __name__,
        info=info
    )
    # app = Flask(__name__)
    app.config.from_object(Config)

    # Register blueprints here
    from views.ai_analysis_view import ai_analysis_bp
    from views.public_fund_view import public_fund_bp
    from views.stock_view import stock_bp
    
    app.register_blueprint(ai_analysis_bp)
    app.register_blueprint(public_fund_bp)
    app.register_blueprint(stock_bp)

    @app.route('/')
    def hello_world():
        return jsonify(message="Hello from FundMasterAI Market Backend!")

    @app.route('/app')
    def frontend_app_redirect():
        return redirect('/app/ai-insights.html')

    @app.route('/app/')
    def frontend_app_index():
        return redirect('/app/ai-insights.html')

    @app.route('/app/<path:filename>')
    def frontend_app(filename):
        return send_from_directory(FRONTEND_DIR, filename)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(port=app.config["HTTP_PORT"], debug=True)
