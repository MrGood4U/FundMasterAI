

from flask import Flask, jsonify
from flask_openapi3 import OpenAPI, Info
from config import Config

def create_app():
    info = Info(title="market backend API document", version="1.0.0")
    app = OpenAPI(
        __name__,
        info=info
    )
    # app = Flask(__name__)
    app.config.from_object(Config)

    # Register blueprints here
    from views.public_fund_view import public_fund_bp
    from views.stock_view import stock_bp
    
    app.register_blueprint(public_fund_bp)
    app.register_blueprint(stock_bp)

    @app.route('/')
    def hello_world():
        return jsonify(message="Hello from FundMasterAI Market Backend!")

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(port=app.config["HTTP_PORT"], debug=True)
