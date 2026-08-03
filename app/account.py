from datetime import date

from flask import Blueprint, jsonify, render_template, send_file
from flask_login import current_user
from sqlalchemy import or_

from .models import Asistencia, Evento
from .permissions import linked_persona_required

account = Blueprint("account", __name__)


def _upcoming_events(person):
    return (
        Evento.query.filter(
            Evento.fecha >= date.today(),
            Evento.estado == "abierto",
            or_(Evento.sede.is_(None), Evento.sede == "", Evento.sede == person.sede),
        )
        .order_by(Evento.fecha, Evento.hora_inicio)
        .all()
    )


def _attended_events(person):
    return (
        Asistencia.query.filter_by(persona_id=person.id)
        .order_by(Asistencia.fecha_hora.desc())
        .all()
    )


@account.get("/mi-cuenta")
@linked_persona_required
def home():
    person = current_user.persona
    return render_template(
        "account/home.html",
        persona=person,
        asistencias=_attended_events(person),
        proximos=_upcoming_events(person),
    )


@account.get("/mi-qr")
@linked_persona_required
def my_qr_page():
    return render_template("account/qr.html", persona=current_user.persona)


@account.get("/mi-informacion")
@linked_persona_required
def my_information():
    return render_template("account/information.html", persona=current_user.persona)


@account.get("/mis-eventos")
@linked_persona_required
def my_events():
    person = current_user.persona
    return render_template(
        "account/events.html",
        asistencias=_attended_events(person),
        proximos=_upcoming_events(person),
    )


@account.get("/api/mi-cuenta")
@linked_persona_required
def my_account_api():
    person = current_user.persona
    return jsonify(success=True, data=person.to_dict())


@account.get("/api/mi-cuenta/qr")
@linked_persona_required
def my_qr_api():
    import io
    import qrcode

    person = current_user.persona
    image = qrcode.make(person.qr_token)
    output = io.BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    return send_file(
        output, mimetype="image/png", download_name=f"qr-{person.codigo}.png"
    )


@account.get("/api/mi-cuenta/eventos")
@linked_persona_required
def my_events_api():
    person = current_user.persona
    data = {
        "asistencias": [item.to_dict() for item in _attended_events(person)],
        "proximos": [item.to_dict() for item in _upcoming_events(person)],
    }
    return jsonify(success=True, data=data)
