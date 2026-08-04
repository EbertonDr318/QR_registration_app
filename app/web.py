from datetime import date

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func

from .models import Asistencia, Evento, MembresiaIglesia, Persona
from .permissions import admin_required, get_current_iglesia, get_current_membership

web = Blueprint("web", __name__)


@web.get("/")
def entrypoint():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    membership = get_current_membership()
    if not membership:
        from .auth import destination_after_login

        return redirect(destination_after_login(current_user))
    return redirect(
        url_for("web.admin_dashboard" if membership.is_admin else "account.home")
    )


@web.get("/admin")
@admin_required
def admin_dashboard():
    church = get_current_iglesia()
    stats = {
        "personas": Persona.query.filter_by(iglesia_id=church.id).count(),
        "activas": Persona.query.filter_by(iglesia_id=church.id, activo=True).count(),
        "inactivas": Persona.query.filter_by(
            iglesia_id=church.id, activo=False
        ).count(),
        "eventos": Evento.query.filter_by(iglesia_id=church.id).count(),
        "hoy": Asistencia.query.filter(
            Asistencia.iglesia_id == church.id,
            func.date(Asistencia.fecha_hora) == date.today(),
        ).count(),
        "pendientes": MembresiaIglesia.query.filter_by(
            iglesia_id=church.id, estado="pendiente"
        ).count(),
    }
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recientes=Asistencia.query.filter_by(iglesia_id=church.id)
        .order_by(Asistencia.fecha_hora.desc())
        .limit(8)
        .all(),
        eventos=Evento.query.filter_by(iglesia_id=church.id)
        .order_by(Evento.fecha.desc())
        .all(),
    )


@web.get("/admin/personas")
@admin_required
def admin_people():
    church = get_current_iglesia()
    people = (
        Persona.query.filter_by(iglesia_id=church.id).order_by(Persona.apellidos).all()
    )
    return render_template("admin/personas.html", personas=people)


@web.get("/admin/eventos")
@admin_required
def admin_events():
    church = get_current_iglesia()
    events = (
        Evento.query.filter_by(iglesia_id=church.id).order_by(Evento.fecha.desc()).all()
    )
    return render_template("admin/eventos.html", eventos=events)


@web.get("/admin/escaner")
@admin_required
def admin_scanner():
    church = get_current_iglesia()
    events = (
        Evento.query.filter_by(iglesia_id=church.id, estado="abierto")
        .order_by(Evento.fecha.desc())
        .all()
    )
    return render_template("admin/escaner.html", eventos=events)


@web.get("/admin/asistencias")
@admin_required
def admin_attendance():
    church = get_current_iglesia()
    events = (
        Evento.query.filter_by(iglesia_id=church.id).order_by(Evento.fecha.desc()).all()
    )
    return render_template("admin/asistencias.html", eventos=events)


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
    return redirect(url_for(mapping[request.path]), code=308)
