from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from . import db
from .audit import record_audit
from .models import MembresiaIglesia, Persona
from .permissions import admin_required, get_current_iglesia

admin = Blueprint("admin", __name__)


def _tenant_membership_or_404(membership_id):
    church = get_current_iglesia()
    membership = MembresiaIglesia.query.filter_by(
        id=membership_id, iglesia_id=church.id
    ).first()
    if not membership:
        abort(404)
    return membership


def _ensure_admin_remains(membership, new_role=None, new_state=None):
    removes_admin = membership.is_admin and (
        new_role == "usuario" or new_state in {"suspendido", "rechazado"}
    )
    if not removes_admin:
        return
    active_admins = MembresiaIglesia.query.filter_by(
        iglesia_id=membership.iglesia_id,
        rol="admin",
        estado="activo",
    ).count()
    if active_admins <= 1:
        abort(
            409,
            description="La iglesia debe conservar al menos un administrador activo.",
        )


@admin.get("/admin/membresias")
@admin_required
def memberships():
    church = get_current_iglesia()
    rows = (
        MembresiaIglesia.query.filter_by(iglesia_id=church.id)
        .order_by(MembresiaIglesia.fecha_solicitud.desc())
        .all()
    )
    people = (
        Persona.query.filter_by(iglesia_id=church.id, activo=True)
        .order_by(Persona.apellidos)
        .all()
    )
    return render_template("admin/memberships.html", memberships=rows, people=people)


@admin.get("/admin/configuracion")
@admin_required
def settings():
    return render_template("admin/settings.html", iglesia=get_current_iglesia())


@admin.post("/admin/membresias/<int:membership_id>/estado")
@admin_required
def membership_status(membership_id):
    membership = _tenant_membership_or_404(membership_id)
    state = request.form.get("estado")
    allowed = {"activo", "suspendido", "rechazado"}
    if state not in allowed:
        abort(400)
    if state == "activo" and membership.is_regular_user and not membership.persona:
        abort(400, description="Vincula una persona antes de activar esta membresía.")
    _ensure_admin_remains(membership, new_state=state)
    previous = membership.estado
    membership.estado = state
    if state == "activo":
        membership.fecha_aprobacion = datetime.now()
        membership.aprobado_por_id = current_user.id
    action = {
        "activo": (
            "aprobar_membresia" if previous == "pendiente" else "reactivar_membresia"
        ),
        "suspendido": "suspender_membresia",
        "rechazado": "rechazar_membresia",
    }[state]
    record_audit(
        membership.iglesia_id,
        action,
        "membresia",
        membership.id,
        {"estado_anterior": previous, "estado_nuevo": state},
    )
    db.session.commit()
    flash("Estado de membresía actualizado.", "success")
    return redirect(url_for("admin.memberships"))


@admin.post("/admin/membresias/<int:membership_id>/rol")
@admin_required
def membership_role(membership_id):
    membership = _tenant_membership_or_404(membership_id)
    role = request.form.get("rol")
    if role not in {"usuario", "admin"}:
        abort(400)
    if role == "usuario" and not membership.persona:
        abort(400, description="Vincula una persona antes de asignar el rol usuario.")
    _ensure_admin_remains(membership, new_role=role)
    previous = membership.rol
    membership.rol = role
    record_audit(
        membership.iglesia_id,
        "cambiar_rol",
        "membresia",
        membership.id,
        {"rol_anterior": previous, "rol_nuevo": role},
    )
    db.session.commit()
    flash("Rol actualizado.", "success")
    return redirect(url_for("admin.memberships"))


@admin.post("/admin/membresias/<int:membership_id>/persona")
@admin_required
def membership_person(membership_id):
    membership = _tenant_membership_or_404(membership_id)
    person_id = request.form.get("persona_id", type=int)
    person = Persona.query.filter_by(
        id=person_id, iglesia_id=membership.iglesia_id
    ).first()
    if not person:
        abort(404)
    membership.persona = person
    record_audit(
        membership.iglesia_id,
        "vincular_persona",
        "membresia",
        membership.id,
        {"persona_id": person.id},
    )
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, description="La persona ya está vinculada a otra membresía.")
    flash("Persona vinculada.", "success")
    return redirect(url_for("admin.memberships"))
