from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def linked_persona_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if (
            current_user.is_admin
            or not current_user.persona
            or not current_user.persona.activo
        ):
            abort(403)
        return view(*args, **kwargs)

    return wrapped
