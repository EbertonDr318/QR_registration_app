from datetime import date

from flask import Blueprint, flash, jsonify, redirect, render_template, request, send_file, url_for
from sqlalchemy import or_

from .models import Asistencia, Evento
from . import db
from .audit import record_audit
from .services.qr_documents import build_qr_card_pdf
from .profile_fields import GROUPS, normalize_group, valid_phone
from .permissions import (
    get_current_iglesia,
    get_current_membership,
    linked_persona_required,
)

account = Blueprint("account", __name__)


def _upcoming_events(person, iglesia_id):
    return (
        Evento.query.filter(
            Evento.iglesia_id == iglesia_id,
            Evento.fecha >= date.today(),
            Evento.estado == "abierto",
            or_(Evento.sede.is_(None), Evento.sede == "", Evento.sede == person.sede),
        )
        .order_by(Evento.fecha, Evento.hora_inicio)
        .all()
    )


def _attended_events(person, iglesia_id):
    return (
        Asistencia.query.filter_by(
            iglesia_id=iglesia_id,
            persona_id=person.id,
        )
        .order_by(Asistencia.fecha_hora.desc())
        .all()
    )


def _account_context():
    membership = get_current_membership()
    person = membership.persona
    iglesia = get_current_iglesia()
    attendances = _attended_events(person, iglesia.id)
    return {
        "membership": membership,
        "persona": person,
        "iglesia": iglesia,
        "asistencias": attendances,
        "ultima_asistencia": attendances[0] if attendances else None,
        "proximos": _upcoming_events(person, iglesia.id),
        "groups": GROUPS,
    }


@account.get("/mi-cuenta")
@linked_persona_required
def home():
    return render_template("account/home.html", **_account_context())


@account.get("/mi-cuenta/qr")
@account.get("/mi-qr")
@linked_persona_required
def my_qr_page():
    return render_template("account/qr.html", **_account_context())


@account.get("/mi-cuenta/informacion")
@account.get("/mi-informacion")
@linked_persona_required
def my_information():
    return render_template("account/information.html", **_account_context())


@account.post("/mi-cuenta/informacion")
@linked_persona_required
def update_my_information():
    """Permite editar solo los datos personales no privilegiados de la ficha propia."""
    membership = get_current_membership()
    person = membership.persona
    fields = {"nombres": 80, "apellidos": 80, "telefono": 25, "sede": 80, "grupo": 80}
    values = {key: str(request.form.get(key) or "").strip()[:limit] for key, limit in fields.items()}
    if not values["nombres"] or not values["apellidos"]:
        flash("Nombre y apellidos son obligatorios.", "error")
        return redirect(url_for("account.my_information"))
    if not valid_phone(values["telefono"]):
        flash("El teléfono solo puede contener números.", "error")
        return redirect(url_for("account.my_information"))
    group = normalize_group(values["grupo"])
    if values["grupo"] and not group:
        flash("Selecciona un grupo válido.", "error")
        return redirect(url_for("account.my_information"))
    values["grupo"] = group or ""
    for key, value in values.items():
        setattr(person, key, value or None)
    record_audit(person.iglesia_id, "actualizar_perfil_propio", "persona", person.id)
    db.session.commit()
    flash("Tu información fue actualizada.", "success")
    return redirect(url_for("account.my_information"))


@account.get("/mi-cuenta/eventos")
@account.get("/mis-eventos")
@linked_persona_required
def my_events():
    return render_template("account/events.html", **_account_context())


@account.get("/api/mi-cuenta")
@linked_persona_required
def my_account_api():
    context = _account_context()
    data = context["persona"].to_dict()
    data["iglesia"] = context["iglesia"].nombre
    return jsonify(success=True, data=data)


@account.get("/api/mi-cuenta/qr")
@linked_persona_required
def my_qr_api():
    import io
    import qrcode

    person = get_current_membership().persona
    image = qrcode.make(person.qr_token)
    output = io.BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    return send_file(
        output,
        mimetype="image/png",
        download_name=f"qr-{person.codigo}.png",
        as_attachment=True,
    )


@account.get("/api/mi-cuenta/qr.pdf")
@linked_persona_required
def my_qr_pdf():
    """Permite al usuario descargar únicamente su propio carnet QR."""
    context = _account_context()
    person = context["persona"]
    return send_file(
        build_qr_card_pdf(person, context["iglesia"]),
        mimetype="application/pdf",
        download_name=f"carnet-{person.codigo}.pdf",
        as_attachment=True,
    )


@account.get("/api/mi-cuenta/eventos")
@linked_persona_required
def my_events_api():
    context = _account_context()
    data = {
        "asistencias": [item.to_dict() for item in context["asistencias"]],
        "proximos": [item.to_dict() for item in context["proximos"]],
    }
    return jsonify(success=True, data=data)
