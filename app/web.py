from datetime import date
from flask import Blueprint, render_template
from sqlalchemy import func
from .models import Persona, Evento, Asistencia

web=Blueprint("web",__name__)
@web.get("/")
def dashboard():
    stats={"personas":Persona.query.count(),"activas":Persona.query.filter_by(activo=True).count(),"inactivas":Persona.query.filter_by(activo=False).count(),"eventos":Evento.query.count(),"hoy":Asistencia.query.filter(func.date(Asistencia.fecha_hora)==date.today()).count()}
    return render_template("dashboard.html",stats=stats,recientes=Asistencia.query.order_by(Asistencia.fecha_hora.desc()).limit(8).all(),eventos=Evento.query.order_by(Evento.fecha.desc()).all())
@web.get("/personas")
def personas():return render_template("personas.html",personas=Persona.query.order_by(Persona.apellidos).all())
@web.get("/eventos")
def eventos():return render_template("eventos.html",eventos=Evento.query.order_by(Evento.fecha.desc()).all())
@web.get("/escaner")
def escaner():return render_template("escaner.html",eventos=Evento.query.filter_by(estado="abierto").order_by(Evento.fecha.desc()).all())
@web.get("/asistencias")
def asistencias():return render_template("asistencias.html",eventos=Evento.query.order_by(Evento.fecha.desc()).all())
