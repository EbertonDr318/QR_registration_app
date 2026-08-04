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
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func

from . import db, oauth
from .audit import record_audit
from .models import Iglesia, MembresiaIglesia, Persona, Usuario

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


def _google_callback_url():
    base_url = current_app.config["PUBLIC_BASE_URL"]
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError("PUBLIC_BASE_URL no es una URL válida.")
    if current_app.config.get("APP_ENV") == "production" and parsed.scheme != "https":
        raise RuntimeError("PUBLIC_BASE_URL debe usar HTTPS en producción.")
    return f"{base_url}{url_for('auth.google_callback')}"


def _membership_destination(membership):
    return url_for("web.admin_dashboard" if membership.is_admin else "account.home")


def _active_memberships(user):
    return (
        MembresiaIglesia.query.join(Iglesia)
        .filter(
            MembresiaIglesia.usuario_id == user.id,
            MembresiaIglesia.estado == "activo",
            Iglesia.activa.is_(True),
        )
        .order_by(Iglesia.nombre)
        .all()
    )


def destination_after_login(user):
    memberships = _active_memberships(user)
    session.pop("iglesia_id", None)
    if len(memberships) == 1:
        session["iglesia_id"] = memberships[0].iglesia_id
        return _membership_destination(memberships[0])
    if len(memberships) > 1:
        return url_for("auth.select_church")
    return url_for("auth.join_church")


def authenticate_claims(claims):
    """Valida claims OIDC sin aceptar roles ni identificadores del navegador."""
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
        user = Usuario(
            email=email,
            nombre=str(claims.get("name") or email)[:160],
            proveedor="google",
            proveedor_subject=subject,
            activo=True,
        )
        db.session.add(user)

    if not user.activo:
        return None, "Esta cuenta está inactiva."

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
        return redirect(destination_after_login(current_user))
    return render_template("auth/login.html")


@auth.get("/auth/google")
def google_login():
    if not current_app.config.get("GOOGLE_CLIENT_ID"):
        flash("El acceso con Google todavía no está configurado.", "error")
        return redirect(url_for("auth.login"))
    redirect_uri = _google_callback_url()
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

    session.clear()
    login_user(user)
    logger.info("Acceso correcto por Google para usuario id=%s", user.id)
    return redirect(destination_after_login(user))


@auth.get("/seleccionar-iglesia")
@login_required
def select_church():
    memberships = _active_memberships(current_user)
    if len(memberships) == 1:
        session["iglesia_id"] = memberships[0].iglesia_id
        return redirect(_membership_destination(memberships[0]))
    if not memberships:
        return redirect(url_for("auth.join_church"))
    return render_template("auth/select_church.html", memberships=memberships)


def _select_authorized_church(iglesia_id):
    membership = (
        MembresiaIglesia.query.join(Iglesia)
        .filter(
            MembresiaIglesia.usuario_id == current_user.id,
            MembresiaIglesia.iglesia_id == iglesia_id,
            MembresiaIglesia.estado == "activo",
            Iglesia.activa.is_(True),
        )
        .first()
    )
    if not membership:
        return None

    previous = session.get("iglesia_id")
    session["iglesia_id"] = membership.iglesia_id
    if previous and previous != membership.iglesia_id:
        record_audit(
            membership.iglesia_id,
            "cambiar_iglesia",
            "iglesia",
            membership.iglesia_id,
            {"iglesia_anterior_id": previous},
        )
        db.session.commit()
    return membership


@auth.post("/seleccionar-iglesia")
@login_required
def select_church_post():
    membership = _select_authorized_church(request.form.get("iglesia_id", type=int))
    if not membership:
        return render_template("errors/403.html"), 403
    return redirect(_membership_destination(membership))


@auth.post("/cambiar-iglesia")
@login_required
def change_church():
    membership = _select_authorized_church(request.form.get("iglesia_id", type=int))
    if not membership:
        return render_template("errors/403.html"), 403
    return redirect(_membership_destination(membership))


@auth.route("/unirse", methods=["GET", "POST"])
@login_required
def join_church():
    churches = Iglesia.query.filter_by(activa=True).order_by(Iglesia.nombre).all()
    if request.method == "GET":
        return render_template("auth/join_church.html", churches=churches)

    iglesia_id = request.form.get("iglesia_id", type=int)
    church = Iglesia.query.filter_by(id=iglesia_id, activa=True).first()
    if not church:
        return render_template("errors/403.html"), 403

    existing = MembresiaIglesia.query.filter_by(
        usuario_id=current_user.id, iglesia_id=church.id
    ).first()
    if existing:
        flash("Ya existe una solicitud o membresía para esta iglesia.", "error")
        return redirect(url_for("auth.join_church"))

    people = Persona.query.filter(
        Persona.iglesia_id == church.id,
        Persona.activo.is_(True),
        func.lower(func.trim(Persona.correo)) == current_user.email,
    ).all()
    membership = MembresiaIglesia(
        usuario=current_user,
        iglesia=church,
        rol="usuario",
        estado="activo" if len(people) == 1 else "pendiente",
        persona=people[0] if len(people) == 1 else None,
        fecha_aprobacion=datetime.now() if len(people) == 1 else None,
    )
    db.session.add(membership)
    db.session.commit()

    if membership.estado == "activo":
        session["iglesia_id"] = church.id
        return redirect(url_for("account.home"))
    flash("Tu solicitud quedó pendiente de revisión por un administrador.", "success")
    return redirect(url_for("auth.join_church"))


@auth.post("/logout")
def logout():
    if current_user.is_authenticated:
        logger.info("Cierre de sesión para usuario id=%s", current_user.id)
    session.clear()
    logout_user()
    return redirect(url_for("auth.login"))
