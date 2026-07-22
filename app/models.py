from datetime import datetime
from . import db

class Persona(db.Model):
    __tablename__ = "personas"
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(30), unique=True, nullable=False, index=True)
    nombres = db.Column(db.String(80), nullable=False)
    apellidos = db.Column(db.String(80), nullable=False)
    correo = db.Column(db.String(120))
    telefono = db.Column(db.String(25))
    sede = db.Column(db.String(80), index=True)
    grupo = db.Column(db.String(80), index=True)
    qr_token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    activo = db.Column(db.Boolean, nullable=False, default=True, index=True)
    fecha_registro = db.Column(db.DateTime, nullable=False, default=datetime.now)
    fecha_actualizacion = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    asistencias = db.relationship("Asistencia", back_populates="persona", cascade="all, delete-orphan")

    def to_dict(self):
        return {k: getattr(self, k) for k in ("id", "codigo", "nombres", "apellidos", "correo", "telefono", "sede", "grupo", "activo")}

class Evento(db.Model):
    __tablename__ = "eventos"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.String(500))
    fecha = db.Column(db.Date, nullable=False, index=True)
    hora_inicio = db.Column(db.Time, nullable=False)
    sede = db.Column(db.String(80), index=True)
    estado = db.Column(db.String(10), nullable=False, default="abierto", index=True)
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=datetime.now)
    fecha_actualizacion = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    asistencias = db.relationship("Asistencia", back_populates="evento", cascade="all, delete-orphan")

    def to_dict(self):
        return {"id": self.id, "nombre": self.nombre, "descripcion": self.descripcion, "fecha": self.fecha.isoformat(), "hora_inicio": self.hora_inicio.strftime("%H:%M"), "sede": self.sede, "estado": self.estado}

class Asistencia(db.Model):
    __tablename__ = "asistencias"
    __table_args__ = (db.UniqueConstraint("persona_id", "evento_id", name="uq_asistencia_persona_evento"),)
    id = db.Column(db.Integer, primary_key=True)
    persona_id = db.Column(db.Integer, db.ForeignKey("personas.id", ondelete="CASCADE"), nullable=False, index=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("eventos.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha_hora = db.Column(db.DateTime, nullable=False, default=datetime.now, index=True)
    metodo_registro = db.Column(db.String(20), nullable=False, default="qr")
    persona = db.relationship("Persona", back_populates="asistencias")
    evento = db.relationship("Evento", back_populates="asistencias")

    def to_dict(self):
        return {"id": self.id, "persona_id": self.persona_id, "persona": f"{self.persona.nombres} {self.persona.apellidos}", "codigo": self.persona.codigo, "evento_id": self.evento_id, "evento": self.evento.nombre, "sede": self.persona.sede, "grupo": self.persona.grupo, "fecha_hora": self.fecha_hora.isoformat(), "metodo_registro": self.metodo_registro}
