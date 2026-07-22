import os
import logging
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

db = SQLAlchemy()

def create_app(test_config=None):
    load_dotenv()
    app = Flask(__name__)
    password = os.getenv("DB_PASSWORD", "")
    mysql_uri = (f"mysql+pymysql://{os.getenv('DB_USER', 'root')}:{password}"
                   f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}"
                   f"/{os.getenv('DB_NAME', 'asistencia_qr')}?charset=utf8mb4")
    database_uri = os.getenv("DATABASE_URL") or mysql_uri
    if database_uri.startswith("mysql://"):
        database_uri = database_uri.replace("mysql://", "mysql+pymysql://", 1)
    is_production = os.getenv("APP_ENV") == "production"
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", "change-this-in-production"),
        SQLALCHEMY_DATABASE_URI=database_uri,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JSON_SORT_KEYS=False,
        DEBUG=False if is_production else os.getenv("FLASK_DEBUG", "0") == "1",
        SESSION_COOKIE_SECURE=is_production,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)
    db.init_app(app)
    from .api import api
    from .web import web
    app.register_blueprint(api, url_prefix="/api")
    app.register_blueprint(web)
    logging.basicConfig(level=logging.INFO)

    @app.get("/health")
    def health():
        return jsonify(status="ok"), 200

    @app.errorhandler(404)
    def not_found(error):
        if __import__('flask').request.path.startswith('/api/'):
            return jsonify(success=False, message="Recurso inexistente", errors={}), 404
        return error

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify(success=False, message="Error interno del servidor", errors={}), 500
    return app
