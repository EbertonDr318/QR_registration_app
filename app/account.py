from datetime import date

from flask import Blueprint, jsonify, render_template, send_file
from sqlalchemy import or_

from .models import Asistencia, Evento
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
    }


@account.get("/mi-cuenta")
@linked_persona_required
def home():
    return render_template("account/home.html", **_account_context())


@account.get("/mi-qr")
@linked_persona_required
def my_qr_page():
    return render_template("account/qr.html", **_account_context())


@account.get("/mi-informacion")
@linked_persona_required
def my_information():
    return render_template("account/information.html", **_account_context())


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


@account.get("/api/mi-cuenta/eventos")
@linked_persona_required
def my_events_api():
    context = _account_context()
    data = {
        "asistencias": [item.to_dict() for item in context["asistencias"]],
        "proximos": [item.to_dict() for item in context["proximos"]],
    }
    return jsonify(success=True, data=data)
