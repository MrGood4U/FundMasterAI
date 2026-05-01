

from flask import Flask, jsonify
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register blueprints here
    from views.news_view import news_bp
    app.register_blueprint(news_bp)

    @app.route('/')
    def hello_world():
        return jsonify(message="Hello from FundMasterAI Backend!")

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
