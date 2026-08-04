from functools import wraps

from flask import abort, g, session
from flask_login import current_user, login_required

from . import db
from .models import Iglesia, MembresiaIglesia


def get_current_iglesia():
    if "current_iglesia" not in g:
        iglesia_id = session.get("iglesia_id")
        g.current_iglesia = (
            db.session.get(Iglesia, iglesia_id) if iglesia_id is not None else None
        )
    return g.current_iglesia


def get_current_membership():
    if "current_membership" not in g:
        iglesia = get_current_iglesia()
        g.current_membership = None
        if current_user.is_authenticated and iglesia and iglesia.activa:
            g.current_membership = MembresiaIglesia.query.filter_by(
                usuario_id=current_user.id,
                iglesia_id=iglesia.id,
                estado="activo",
            ).first()
    return g.current_membership


def iglesia_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not get_current_membership():
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        membership = get_current_membership()
        if not membership or not membership.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def linked_persona_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        membership = get_current_membership()
        if (
            not membership
            or not membership.is_regular_user
            or not membership.persona
            or not membership.persona.activo
        ):
            abort(403)
        return view(*args, **kwargs)

    return wrapped
