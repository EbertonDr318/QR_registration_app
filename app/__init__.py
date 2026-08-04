import logging
import os
from urllib.parse import urlparse

from authlib.integrations.flask_client import OAuth
from flask import Flask, jsonify
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix

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
        APP_ENV="production" if is_production else "development",
        SECRET_KEY=os.getenv("SECRET_KEY") or "change-this-in-production",
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
        GOOGLE_DISCOVERY_URL=os.getenv(
            "GOOGLE_DISCOVERY_URL",
            "https://accounts.google.com/.well-known/openid-configuration",
        ),
        PUBLIC_BASE_URL=(
            os.getenv("PUBLIC_BASE_URL") or "http://localhost:5000"
        ).rstrip("/"),
        PREFERRED_URL_SCHEME="https" if is_production else "http",
    )
    if test_config:
        app.config.update(test_config)
    if is_production and app.config["SECRET_KEY"] == "change-this-in-production":
        raise RuntimeError("SECRET_KEY debe configurarse en producción.")
    public_base_url = urlparse(app.config["PUBLIC_BASE_URL"])
    if is_production and (
        public_base_url.scheme != "https" or not public_base_url.netloc
    ):
        raise RuntimeError("PUBLIC_BASE_URL debe ser una URL HTTPS en producción.")
    if is_production:
        # Railway finaliza TLS en su proxy; se confía sólo en un salto conocido.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
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
        server_metadata_url=app.config["GOOGLE_DISCOVERY_URL"],
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
    from .admin import admin
    from .auth import auth
    from .web import web

    app.register_blueprint(api, url_prefix="/api")
    app.register_blueprint(account)
    app.register_blueprint(admin)
    app.register_blueprint(auth)
    app.register_blueprint(web)
    from .cli import churches_cli, memberships_cli

    app.cli.add_command(churches_cli)
    app.cli.add_command(memberships_cli)
    logging.basicConfig(level=logging.INFO)

    @app.context_processor
    def tenant_context():
        from flask_login import current_user

        from .models import Iglesia, MembresiaIglesia
        from .permissions import get_current_iglesia, get_current_membership

        memberships = []
        if current_user.is_authenticated:
            memberships = (
                MembresiaIglesia.query.join(Iglesia)
                .filter(
                    MembresiaIglesia.usuario_id == current_user.id,
                    MembresiaIglesia.estado == "activo",
                    Iglesia.activa.is_(True),
                )
                .order_by(Iglesia.nombre)
                .all()
            )
        return {
            "current_iglesia": get_current_iglesia(),
            "current_membership": get_current_membership(),
            "active_memberships": memberships,
        }

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
