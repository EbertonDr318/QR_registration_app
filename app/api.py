import csv, io, re, secrets
from datetime import date, datetime, time
from flask import Blueprint, jsonify, request, send_file
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from . import db
from .models import Persona, Evento, Asistencia

api = Blueprint("api", __name__)
EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

def ok(message, data=None, status=200): return jsonify(success=True, message=message, data=data), status
def fail(message, status=400, errors=None): return jsonify(success=False, message=message, errors=errors or {}), status
def clean(value, limit): return str(value or "").strip()[:limit]

def persona_data(payload, partial=False):
    fields = {"codigo": 30, "nombres": 80, "apellidos": 80, "correo": 120, "telefono": 25, "sede": 80, "grupo": 80}
    data = {k: clean(payload.get(k), n) for k, n in fields.items() if k in payload or not partial}
    errors = {}
    for key in ("codigo", "nombres", "apellidos"):
        if not partial and not data.get(key): errors[key] = "Campo obligatorio"
        if key in data and not data[key]: errors[key] = "No puede estar vacío"
    if data.get("correo") and not EMAIL.match(data["correo"]): errors["correo"] = "Correo inválido"
    if "activo" in payload: data["activo"] = bool(payload["activo"])
    return data, errors

@api.get("/personas")
def personas_list():
    query = Persona.query
    q = clean(request.args.get("q"), 100)
    if q: query = query.filter(or_(Persona.nombres.ilike(f"%{q}%"), Persona.apellidos.ilike(f"%{q}%"), Persona.codigo.ilike(f"%{q}%")))
    for field in ("sede", "grupo"):
        if request.args.get(field): query = query.filter(getattr(Persona, field) == request.args[field])
    if request.args.get("activo") in ("true", "false"): query = query.filter_by(activo=request.args["activo"] == "true")
    return ok("Personas consultadas", [p.to_dict() for p in query.order_by(Persona.apellidos).all()])

@api.get("/personas/<int:pid>")
def persona_get(pid):
    p = db.get_or_404(Persona, pid); return ok("Persona consultada", p.to_dict())

@api.post("/personas")
def persona_create():
    data, errors = persona_data(request.get_json(silent=True) or {})
    if errors: return fail("Datos inválidos", errors=errors)
    p = Persona(**data, qr_token=secrets.token_urlsafe(32))
    db.session.add(p)
    try: db.session.commit()
    except IntegrityError: db.session.rollback(); return fail("El código interno ya existe", 409, {"codigo": "Debe ser único"})
    return ok("Persona registrada correctamente", p.to_dict(), 201)

@api.put("/personas/<int:pid>")
def persona_update(pid):
    p = db.get_or_404(Persona, pid); data, errors = persona_data(request.get_json(silent=True) or {})
    if errors: return fail("Datos inválidos", errors=errors)
    for k, v in data.items(): setattr(p, k, v)
    try: db.session.commit()
    except IntegrityError: db.session.rollback(); return fail("El código interno ya existe", 409)
    return ok("Persona actualizada", p.to_dict())

@api.patch("/personas/<int:pid>/estado")
def persona_estado(pid):
    p = db.get_or_404(Persona, pid); p.activo = bool((request.get_json(silent=True) or {}).get("activo")); db.session.commit(); return ok("Estado actualizado", p.to_dict())

@api.post("/personas/<int:pid>/regenerar-qr")
def persona_regenerar(pid):
    p = db.get_or_404(Persona, pid); p.qr_token = secrets.token_urlsafe(32); db.session.commit(); return ok("Token QR regenerado", p.to_dict())

@api.get("/personas/<int:pid>/qr")
def persona_qr(pid):
    import qrcode
    p = db.get_or_404(Persona, pid); image = qrcode.make(p.qr_token); stream = io.BytesIO(); image.save(stream, format="PNG"); stream.seek(0)
    return send_file(stream, mimetype="image/png", download_name=f"qr-{p.codigo}.png", as_attachment=request.args.get("descargar") == "1")

def event_data(payload):
    errors = {}; data = {k: clean(payload.get(k), n) for k,n in {"nombre":120,"descripcion":500,"sede":80}.items()}
    if not data["nombre"]: errors["nombre"] = "Campo obligatorio"
    try: data["fecha"] = date.fromisoformat(payload.get("fecha", ""))
    except ValueError: errors["fecha"] = "Fecha inválida"
    try: data["hora_inicio"] = time.fromisoformat(payload.get("hora_inicio", ""))
    except ValueError: errors["hora_inicio"] = "Hora inválida"
    data["estado"] = payload.get("estado", "abierto")
    if data["estado"] not in ("abierto", "cerrado"): errors["estado"] = "Estado inválido"
    return data, errors

@api.get("/eventos")
def eventos_list(): return ok("Eventos consultados", [e.to_dict() for e in Evento.query.order_by(Evento.fecha.desc()).all()])
@api.get("/eventos/<int:eid>")
def evento_get(eid): return ok("Evento consultado", db.get_or_404(Evento, eid).to_dict())
@api.post("/eventos")
def evento_create():
    data, errors = event_data(request.get_json(silent=True) or {})
    if errors: return fail("Datos inválidos", errors=errors)
    e=Evento(**data); db.session.add(e); db.session.commit(); return ok("Evento creado", e.to_dict(), 201)
@api.put("/eventos/<int:eid>")
def evento_update(eid):
    e=db.get_or_404(Evento,eid); data,errors=event_data(request.get_json(silent=True) or {})
    if errors:return fail("Datos inválidos",errors=errors)
    data["estado"] = e.estado
    for k,v in data.items():setattr(e,k,v)
    db.session.commit();return ok("Evento actualizado",e.to_dict())
@api.patch("/eventos/<int:eid>/estado")
def evento_estado(eid):
    e=db.get_or_404(Evento,eid); estado=(request.get_json(silent=True) or {}).get("estado")
    if estado not in ("abierto","cerrado"):return fail("Estado inválido")
    e.estado=estado;db.session.commit();return ok("Estado actualizado",e.to_dict())

@api.post("/asistencias/registrar")
def registrar():
    payload=request.get_json(silent=True) or {}; eid=payload.get("evento_id")
    if not eid:return fail("Evento no seleccionado")
    evento=db.session.get(Evento,eid)
    if not evento:return fail("Evento inexistente",404)
    if evento.estado!="abierto":return fail("Evento cerrado",409)
    token=clean(payload.get("token"),128); codigo=clean(payload.get("codigo"),30)
    persona=Persona.query.filter_by(qr_token=token).first() if token else Persona.query.filter_by(codigo=codigo).first()
    if not persona:return fail("Código QR inválido" if token else "Persona inexistente",404)
    if not persona.activo:return fail("Persona inactiva",409)
    a=Asistencia(persona=persona,evento=evento,metodo_registro="qr" if token else "manual");db.session.add(a)
    try:db.session.commit()
    except IntegrityError:db.session.rollback();return fail("La persona ya registró asistencia en este evento",409)
    return ok("Asistencia registrada correctamente",a.to_dict(),201)

def attendance_query():
    query=Asistencia.query.join(Persona).join(Evento)
    q=clean(request.args.get("q"),100)
    if q:query=query.filter(or_(Persona.nombres.ilike(f"%{q}%"),Persona.apellidos.ilike(f"%{q}%"),Persona.codigo.ilike(f"%{q}%")))
    if request.args.get("evento_id"):query=query.filter(Asistencia.evento_id==request.args["evento_id"])
    if request.args.get("sede"):query=query.filter(Persona.sede==request.args["sede"])
    try:
        if request.args.get("desde"):query=query.filter(Asistencia.fecha_hora>=datetime.fromisoformat(request.args["desde"]))
        if request.args.get("hasta"):query=query.filter(Asistencia.fecha_hora<datetime.fromisoformat(request.args["hasta"])+__import__('datetime').timedelta(days=1))
    except ValueError:pass
    return query.order_by(Asistencia.fecha_hora.desc())
@api.get("/asistencias")
def asistencias_list():return ok("Asistencias consultadas",[a.to_dict() for a in attendance_query().all()])
@api.get("/asistencias/recientes")
def recientes():return ok("Asistencias recientes",[a.to_dict() for a in Asistencia.query.order_by(Asistencia.fecha_hora.desc()).limit(10)])
@api.get("/asistencias/exportar")
def exportar():
    stream=io.StringIO();stream.write('\ufeff');writer=csv.writer(stream);writer.writerow(["Código","Persona","Evento","Sede","Grupo","Fecha y hora","Método"])
    for a in attendance_query().all():
        d=a.to_dict();writer.writerow([d["codigo"],d["persona"],d["evento"],d["sede"],d["grupo"],d["fecha_hora"],d["metodo_registro"]])
    data=io.BytesIO(stream.getvalue().encode("utf-8"));return send_file(data,mimetype="text/csv; charset=utf-8",as_attachment=True,download_name="asistencias.csv")

@api.get("/asistencias/exportar.xlsx")
def exportar_excel():
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Asistencias"
    sheet.append(["Código", "Persona", "Evento", "Sede", "Grupo", "Fecha y hora", "Método"])
    for attendance in attendance_query().all():
        item = attendance.to_dict()
        sheet.append([item["codigo"], item["persona"], item["evento"], item["sede"], item["grupo"], item["fecha_hora"], item["metodo_registro"]])
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)
    return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="asistencias.xlsx")

@api.get("/asistencias/exportar.pdf")
def exportar_pdf():
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet

    output = io.BytesIO()
    document = SimpleDocTemplate(output, pagesize=landscape(letter))
    rows = [["Código", "Persona", "Evento", "Sede", "Grupo", "Fecha y hora", "Método"]]
    for attendance in attendance_query().all():
        item = attendance.to_dict()
        rows.append([item["codigo"], item["persona"], item["evento"], item["sede"] or "", item["grupo"] or "", item["fecha_hora"], item["metodo_registro"]])
    table = Table(rows, repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3157d5")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.25, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 8), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    document.build([Paragraph("Reporte de asistencia", getSampleStyleSheet()["Title"]), table])
    output.seek(0)
    return send_file(output, mimetype="application/pdf", as_attachment=True, download_name="asistencias.pdf")
