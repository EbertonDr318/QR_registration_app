import logging
import os

from authlib.integrations.flask_client import OAuth
from flask import Flask, jsonify
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
oauth = OAuth()
csrf = CSRFProtect()


def create_app(test_config=None):
    load_dotenv()
    app = Flask(__name__)
    password = os.getenv("DB_PASSWORD", "")
    mysql_uri = (
        f"mysql+pymysql://{os.getenv('DB_USER', 'root')}:{password}"
        f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}"
        f"/{os.getenv('DB_NAME', 'asistencia_qr')}?charset=utf8mb4"
    )
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
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SECURE=is_production,
        REMEMBER_COOKIE_SAMESITE="Lax",
        SESSION_PROTECTION="strong",
        GOOGLE_CLIENT_ID=os.getenv("GOOGLE_CLIENT_ID"),
        GOOGLE_CLIENT_SECRET=os.getenv("GOOGLE_CLIENT_SECRET"),
    )
    if test_config:
        app.config.update(test_config)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.session_protection = "strong"
    oauth.init_app(app)
    csrf.init_app(app)

    oauth.register(
        name="google",
        client_id=app.config.get("GOOGLE_CLIENT_ID"),
        client_secret=app.config.get("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    from .models import Usuario

    @login_manager.user_loader
    def load_user(user_id):
        try:
            user = db.session.get(Usuario, int(user_id))
            return user if user and user.is_active else None
        except (TypeError, ValueError):
            return None

    @login_manager.unauthorized_handler
    def unauthorized():
        from flask import redirect, request, url_for

        if request.path.startswith("/api/"):
            return (
                jsonify(success=False, message="Autenticación requerida", errors={}),
                401,
            )
        return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))

    from .api import api
    from .account import account
    from .auth import auth
    from .web import web

    app.register_blueprint(api, url_prefix="/api")
    app.register_blueprint(account)
    app.register_blueprint(auth)
    app.register_blueprint(web)
    from .cli import users_cli

    app.cli.add_command(users_cli)
    logging.basicConfig(level=logging.INFO)

    @app.get("/health")
    def health():
        return jsonify(status="ok"), 200

    @app.errorhandler(404)
    def not_found(error):
        if __import__("flask").request.path.startswith("/api/"):
            return jsonify(success=False, message="Recurso inexistente", errors={}), 404
        return error

    @app.errorhandler(403)
    def forbidden(error):
        from flask import render_template, request

        if request.path.startswith("/api/"):
            return (
                jsonify(
                    success=False,
                    message="No tienes permisos para esta operación",
                    errors={},
                ),
                403,
            )
        return render_template("errors/403.html"), 403

    from flask_wtf.csrf import CSRFError

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        from flask import request

        if request.path.startswith("/api/"):
            return (
                jsonify(
                    success=False, message="Token CSRF inválido o ausente", errors={}
                ),
                400,
            )
        return "Solicitud inválida: token CSRF ausente o vencido", 400

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        if __import__("flask").request.path.startswith("/api/"):
            return (
                jsonify(success=False, message="Error interno del servidor", errors={}),
                500,
            )
        return "Error interno del servidor", 500

    return app
