import json

from flask import has_request_context
from flask_login import current_user

from . import db
from .models import RegistroAuditoria


def record_audit(iglesia_id, action, entity, entity_id=None, details=None):
    """Registra metadatos operativos; nunca debe recibir secretos ni tokens."""
    safe_details = json.dumps(details or {}, ensure_ascii=False, sort_keys=True)
    entry = RegistroAuditoria(
        iglesia_id=iglesia_id,
        actor_usuario_id=(
            current_user.id
            if has_request_context() and current_user.is_authenticated
            else None
        ),
        accion=action,
        entidad=entity,
        entidad_id=entity_id,
        detalles=safe_details,
    )
    db.session.add(entry)
    return entry
