from datetime import date

from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user
from sqlalchemy import func

from .models import Asistencia, Evento, Persona
from .permissions import admin_required

web = Blueprint("web", __name__)


@web.get("/")
def entrypoint():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    if current_user.is_admin:
        return redirect(url_for("web.admin_dashboard"))
    return redirect(url_for("account.home"))


@web.get("/admin")
@admin_required
def admin_dashboard():
    stats = {
        "personas": Persona.query.count(),
        "activas": Persona.query.filter_by(activo=True).count(),
        "inactivas": Persona.query.filter_by(activo=False).count(),
        "eventos": Evento.query.count(),
        "hoy": Asistencia.query.filter(
            func.date(Asistencia.fecha_hora) == date.today()
        ).count(),
    }
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recientes=Asistencia.query.order_by(Asistencia.fecha_hora.desc())
        .limit(8)
        .all(),
        eventos=Evento.query.order_by(Evento.fecha.desc()).all(),
    )


@web.get("/admin/personas")
@admin_required
def admin_people():
    return render_template(
        "admin/personas.html", personas=Persona.query.order_by(Persona.apellidos).all()
    )


@web.get("/admin/eventos")
@admin_required
def admin_events():
    return render_template(
        "admin/eventos.html", eventos=Evento.query.order_by(Evento.fecha.desc()).all()
    )


@web.get("/admin/escaner")
@admin_required
def admin_scanner():
    events = (
        Evento.query.filter_by(estado="abierto").order_by(Evento.fecha.desc()).all()
    )
    return render_template("admin/escaner.html", eventos=events)


@web.get("/admin/asistencias")
@admin_required
def admin_attendance():
    return render_template(
        "admin/asistencias.html",
        eventos=Evento.query.order_by(Evento.fecha.desc()).all(),
    )


@web.get("/personas")
@web.get("/eventos")
@web.get("/escaner")
@web.get("/asistencias")
@admin_required
def legacy_admin_routes():
    mapping = {
        "/personas": "web.admin_people",
        "/eventos": "web.admin_events",
        "/escaner": "web.admin_scanner",
        "/asistencias": "web.admin_attendance",
    }
    from flask import request

    return redirect(url_for(mapping[request.path]), code=308)
