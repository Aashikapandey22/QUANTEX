"""
QUANTEX Institutional Trading Intelligence Platform
Main Flask Application Server
"""
import os
import logging
from flask import Flask, render_template, send_from_directory
from config import Config
from backend.database import init_db
from backend.routes.api import api_bp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("quantex.app")

def create_app():
    app = Flask(
        __name__,
        template_folder="frontend/templates",
        static_folder="frontend/static"
    )
    app.config.from_object(Config)

    # Initialize Database Schema
    init_db()

    # Register API Blueprint
    app.register_blueprint(api_bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/favicon.ico")
    def favicon():
        return send_from_directory(
            os.path.join(app.root_path, "frontend/static/assets"),
            "favicon.ico",
            mimetype="image/vnd.microsoft.icon"
        )

    logger.info("QUANTEX Institutional Platform initialized successfully.")
    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    logger.info(f"QUANTEX Terminal running at http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=Config.DEBUG)
