"""Creación segura de solicitudes de acceso y fichas personales."""

import re
import secrets

from .. import db
from ..audit import record_audit
from ..models import Iglesia, MembresiaIglesia, Persona, Usuario

CODE_PREFIX = "UX-USER-"
CODE_PATTERN = re.compile(r"^UX-USER-(\d+)$")


def next_person_code(church_id: int) -> str:
    """Obtiene el siguiente código correlativo dentro de una sola iglesia."""
    codes = (
        db.session.query(Persona.codigo)
        .filter(
            Persona.iglesia_id == church_id,
            Persona.codigo.like(f"{CODE_PREFIX}%"),
        )
        .all()
    )
    numbers = [
        int(match.group(1))
        for (code,) in codes
        if (match := CODE_PATTERN.fullmatch(code or ""))
    ]
    return f"{CODE_PREFIX}{max(numbers, default=0) + 1:03d}"


def _person_names(user: Usuario) -> tuple[str, str]:
    parts = str(user.nombre or "Usuario").strip().split(maxsplit=1)
    return parts[0][:80], (parts[1] if len(parts) > 1 else "Pendiente")[:80]


def create_access_request(user: Usuario, church: Iglesia) -> MembresiaIglesia:
    """Crea una ficha y solicitud pendiente, siempre limitada al tenant elegido."""
    existing = MembresiaIglesia.query.filter_by(
        usuario_id=user.id, iglesia_id=church.id
    ).first()
    if existing:
        return existing

    # Bloquear el tenant serializa el correlativo en MySQL y evita códigos
    # duplicados cuando varias personas solicitan acceso al mismo tiempo.
    locked_church = db.session.get(Iglesia, church.id, with_for_update=True)
    nombres, apellidos = _person_names(user)
    person = Persona(
        iglesia=locked_church,
        codigo=next_person_code(church.id),
        nombres=nombres,
        apellidos=apellidos,
        correo=Usuario.normalize_email(user.email),
        qr_token=secrets.token_urlsafe(32),
        activo=True,
    )
    membership = MembresiaIglesia(
        usuario=user,
        iglesia=locked_church,
        persona=person,
        rol="usuario",
        estado="pendiente",
    )
    db.session.add_all([person, membership])
    db.session.flush()
    record_audit(
        church.id,
        "solicitar_acceso",
        "membresia",
        membership.id,
        {"persona_id": person.id, "codigo": person.codigo},
    )
    return membership
