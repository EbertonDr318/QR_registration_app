import logging
from datetime import datetime
from urllib.parse import urljoin, urlparse

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_user, logout_user
from sqlalchemy import func

from . import db, oauth
from .models import Persona, Usuario

auth = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)


def _safe_next_url(target):
    if not target:
        return None
    host = urlparse(request.host_url)
    candidate = urlparse(urljoin(request.host_url, target))
    if candidate.scheme in ("http", "https") and candidate.netloc == host.netloc:
        return candidate.path + (f"?{candidate.query}" if candidate.query else "")
    return None


def _destination(user):
    return url_for("web.admin_dashboard" if user.is_admin else "account.home")


def authenticate_claims(claims):
    """Valida claims OIDC y devuelve (usuario, error) sin depender de Google."""
    email = Usuario.normalize_email(claims.get("email"))
    subject = str(claims.get("sub") or "").strip()
    if not email or not subject or claims.get("email_verified") is not True:
        return None, "Google no proporcionó un correo verificado."

    user = Usuario.query.filter_by(
        proveedor="google", proveedor_subject=subject
    ).first()
    if not user:
        user = Usuario.query.filter(func.lower(Usuario.email) == email).first()

    if not user:
        people = Persona.query.filter(
            Persona.activo.is_(True),
            func.lower(func.trim(Persona.correo)) == email,
        ).all()
        if len(people) != 1:
            reason = (
                "correo duplicado" if len(people) > 1 else "correo sin persona activa"
            )
            logger.warning("Acceso OIDC rechazado: %s (%s)", reason, email)
            return (
                None,
                "Tu cuenta todavía no está habilitada. Contacta a un administrador.",
            )
        person = people[0]
        if person.usuario:
            return None, "La persona ya está vinculada a otra cuenta."
        user = Usuario(
            email=email,
            nombre=str(claims.get("name") or f"{person.nombres} {person.apellidos}")[
                :160
            ],
            proveedor="google",
            proveedor_subject=subject,
            rol="usuario",
            persona=person,
            activo=True,
        )
        db.session.add(user)

    if not user.activo:
        return None, "Esta cuenta está inactiva."
    if user.is_regular_user and (not user.persona or not user.persona.activo):
        return None, "El perfil personal asociado está inactivo."

    user.email = email
    user.nombre = str(claims.get("name") or user.nombre)[:160]
    user.foto_url = str(claims.get("picture") or "")[:500] or None
    user.proveedor = "google"
    user.proveedor_subject = subject
    user.ultimo_acceso = datetime.now()
    db.session.commit()
    return user, None


@auth.get("/login")
def login():
    if current_user.is_authenticated:
        return redirect(_destination(current_user))
    return render_template("auth/login.html")


@auth.get("/auth/google")
def google_login():
    if not current_app.config.get("GOOGLE_CLIENT_ID"):
        flash("El acceso con Google todavía no está configurado.", "error")
        return redirect(url_for("auth.login"))
    redirect_uri = url_for("auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth.get("/auth/google/callback")
def google_callback():
    try:
        token = oauth.google.authorize_access_token()
        claims = token.get("userinfo") or oauth.google.parse_id_token(token)
        user, error = authenticate_claims(claims)
    except Exception:
        logger.exception("Falló el intercambio OIDC con Google")
        user, error = None, "No fue posible completar el acceso con Google."

    if error:
        db.session.rollback()
        flash(error, "error")
        return redirect(url_for("auth.login"))

    login_user(user)
    logger.info("Acceso correcto por Google para usuario id=%s", user.id)
    target = _safe_next_url(request.args.get("next"))
    return redirect(target or _destination(user))


@auth.post("/logout")
def logout():
    if current_user.is_authenticated:
        logger.info("Cierre de sesión para usuario id=%s", current_user.id)
    logout_user()
    return redirect(url_for("auth.login"))
