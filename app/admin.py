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
    return render_template("admin/memberships.html", memberships=rows)


@admin.get("/admin/configuracion")
@admin_required
def settings():
    return render_template("admin/settings.html", iglesia=get_current_iglesia())


@admin.post("/admin/configuracion")
@admin_required
def update_settings():
    """Actualiza únicamente la iglesia activa del administrador autenticado."""
    church = get_current_iglesia()
    nombre = str(request.form.get("nombre") or "").strip()
    ciudad = str(request.form.get("ciudad") or "").strip()
    pais = str(request.form.get("pais") or "").strip()
    zona_horaria = str(request.form.get("zona_horaria") or "").strip()
    descripcion = str(request.form.get("descripcion") or "").strip()

    if len(nombre) < 2 or len(nombre) > 160:
        abort(400, description="El nombre debe contener entre 2 y 160 caracteres.")
    if not pais or len(pais) > 80:
        abort(400, description="El país no es válido.")
    if "/" not in zona_horaria or len(zona_horaria) > 80:
        abort(400, description="La zona horaria no es válida.")
    if len(ciudad) > 120 or len(descripcion) > 500:
        abort(400, description="Uno de los campos supera el límite permitido.")

    previous_name = church.nombre
    church.nombre = nombre
    church.ciudad = ciudad or None
    church.pais = pais
    church.zona_horaria = zona_horaria
    church.descripcion = descripcion or None
    # El slug y el estado no son editables aquí porque identifican y habilitan
    # al tenant; cambiarlos accidentalmente podría cortar el acceso completo.
    record_audit(
        church.id,
        "actualizar_iglesia",
        "iglesia",
        church.id,
        {"nombre_anterior": previous_name, "nombre_nuevo": church.nombre},
    )
    db.session.commit()
    flash("Datos de la iglesia actualizados.", "success")
    return redirect(url_for("admin.settings"))


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
