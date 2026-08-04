from datetime import datetime

from flask_login import UserMixin

from . import db


class Iglesia(db.Model):
    __tablename__ = "iglesias"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(100), nullable=False, unique=True, index=True)
    descripcion = db.Column(db.String(500))
    ciudad = db.Column(db.String(120))
    pais = db.Column(db.String(80), nullable=False, default="Guatemala")
    zona_horaria = db.Column(db.String(80), nullable=False, default="America/Guatemala")
    logo_url = db.Column(db.String(500))
    activa = db.Column(db.Boolean, nullable=False, default=True, index=True)
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=datetime.now)
    fecha_actualizacion = db.Column(
        db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    personas = db.relationship("Persona", back_populates="iglesia")
    eventos = db.relationship("Evento", back_populates="iglesia")
    asistencias = db.relationship(
        "Asistencia", back_populates="iglesia", overlaps="persona,evento,asistencias"
    )
    membresias = db.relationship(
        "MembresiaIglesia",
        back_populates="iglesia",
        cascade="all, delete-orphan",
        overlaps="persona,membresia",
    )

    def to_public_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "slug": self.slug,
            "ciudad": self.ciudad,
            "pais": self.pais,
        }


class Persona(db.Model):
    __tablename__ = "personas"
    __table_args__ = (
        db.UniqueConstraint("iglesia_id", "codigo", name="uq_persona_iglesia_codigo"),
        db.UniqueConstraint("id", "iglesia_id", name="uq_persona_id_iglesia"),
    )

    id = db.Column(db.Integer, primary_key=True)
    iglesia_id = db.Column(
        db.Integer,
        db.ForeignKey("iglesias.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    codigo = db.Column(db.String(30), nullable=False, index=True)
    nombres = db.Column(db.String(80), nullable=False)
    apellidos = db.Column(db.String(80), nullable=False)
    correo = db.Column(db.String(120), index=True)
    telefono = db.Column(db.String(25))
    sede = db.Column(db.String(80), index=True)
    grupo = db.Column(db.String(80), index=True)
    qr_token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    activo = db.Column(db.Boolean, nullable=False, default=True, index=True)
    fecha_registro = db.Column(db.DateTime, nullable=False, default=datetime.now)
    fecha_actualizacion = db.Column(
        db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    iglesia = db.relationship("Iglesia", back_populates="personas")
    asistencias = db.relationship(
        "Asistencia",
        back_populates="persona",
        cascade="all, delete-orphan",
        foreign_keys="Asistencia.persona_id",
        overlaps="iglesia,evento,asistencias",
    )
    membresia = db.relationship(
        "MembresiaIglesia",
        back_populates="persona",
        uselist=False,
        foreign_keys="MembresiaIglesia.persona_id",
        overlaps="iglesia,membresias",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "codigo": self.codigo,
            "nombres": self.nombres,
            "apellidos": self.apellidos,
            "correo": self.correo,
            "telefono": self.telefono,
            "sede": self.sede,
            "grupo": self.grupo,
            "activo": self.activo,
        }


class Evento(db.Model):
    __tablename__ = "eventos"
    __table_args__ = (
        db.UniqueConstraint("id", "iglesia_id", name="uq_evento_id_iglesia"),
    )

    id = db.Column(db.Integer, primary_key=True)
    iglesia_id = db.Column(
        db.Integer,
        db.ForeignKey("iglesias.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    nombre = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.String(500))
    fecha = db.Column(db.Date, nullable=False, index=True)
    hora_inicio = db.Column(db.Time, nullable=False)
    sede = db.Column(db.String(80), index=True)
    estado = db.Column(db.String(10), nullable=False, default="abierto", index=True)
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=datetime.now)
    fecha_actualizacion = db.Column(
        db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    iglesia = db.relationship("Iglesia", back_populates="eventos")
    asistencias = db.relationship(
        "Asistencia",
        back_populates="evento",
        cascade="all, delete-orphan",
        foreign_keys="Asistencia.evento_id",
        overlaps="iglesia,persona,asistencias",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "fecha": self.fecha.isoformat(),
            "hora_inicio": self.hora_inicio.strftime("%H:%M"),
            "sede": self.sede,
            "estado": self.estado,
        }


class Asistencia(db.Model):
    __tablename__ = "asistencias"
    __table_args__ = (
        db.UniqueConstraint(
            "persona_id", "evento_id", name="uq_asistencia_persona_evento"
        ),
        db.ForeignKeyConstraint(
            ["persona_id", "iglesia_id"],
            ["personas.id", "personas.iglesia_id"],
            ondelete="CASCADE",
            name="fk_asistencia_persona_iglesia",
        ),
        db.ForeignKeyConstraint(
            ["evento_id", "iglesia_id"],
            ["eventos.id", "eventos.iglesia_id"],
            ondelete="CASCADE",
            name="fk_asistencia_evento_iglesia",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    iglesia_id = db.Column(
        db.Integer,
        db.ForeignKey("iglesias.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    persona_id = db.Column(db.Integer, nullable=False, index=True)
    evento_id = db.Column(db.Integer, nullable=False, index=True)
    fecha_hora = db.Column(
        db.DateTime, nullable=False, default=datetime.now, index=True
    )
    metodo_registro = db.Column(db.String(20), nullable=False, default="qr")

    iglesia = db.relationship(
        "Iglesia", back_populates="asistencias", overlaps="persona,evento,asistencias"
    )
    persona = db.relationship(
        "Persona",
        back_populates="asistencias",
        overlaps="iglesia,evento,asistencias",
        foreign_keys=[persona_id],
    )
    evento = db.relationship(
        "Evento",
        back_populates="asistencias",
        overlaps="iglesia,persona,asistencias",
        foreign_keys=[evento_id],
    )

    def to_dict(self):
        return {
            "id": self.id,
            "persona_id": self.persona_id,
            "persona": f"{self.persona.nombres} {self.persona.apellidos}",
            "codigo": self.persona.codigo,
            "evento_id": self.evento_id,
            "evento": self.evento.nombre,
            "sede": self.persona.sede,
            "grupo": self.persona.grupo,
            "fecha_hora": self.fecha_hora.isoformat(),
            "metodo_registro": self.metodo_registro,
        }


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, unique=True, index=True)
    nombre = db.Column(db.String(160), nullable=False)
    foto_url = db.Column(db.String(500))
    proveedor = db.Column(db.String(30), nullable=False, default="google")
    proveedor_subject = db.Column(db.String(255), unique=True, index=True)
    activo = db.Column(db.Boolean, nullable=False, default=True, index=True)
    ultimo_acceso = db.Column(db.DateTime)
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=datetime.now)
    fecha_actualizacion = db.Column(
        db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    membresias = db.relationship(
        "MembresiaIglesia",
        back_populates="usuario",
        foreign_keys="MembresiaIglesia.usuario_id",
        cascade="all, delete-orphan",
    )

    @staticmethod
    def normalize_email(email):
        return str(email or "").strip().casefold()

    @property
    def is_active(self):
        return bool(self.activo)


class MembresiaIglesia(db.Model):
    __tablename__ = "membresias_iglesia"
    __table_args__ = (
        db.UniqueConstraint(
            "usuario_id", "iglesia_id", name="uq_membresia_usuario_iglesia"
        ),
        db.UniqueConstraint(
            "iglesia_id", "persona_id", name="uq_membresia_iglesia_persona"
        ),
        db.CheckConstraint("rol IN ('usuario', 'admin')", name="ck_membresia_rol"),
        db.CheckConstraint(
            "estado IN ('pendiente', 'activo', 'suspendido', 'rechazado')",
            name="ck_membresia_estado",
        ),
        db.ForeignKeyConstraint(
            ["persona_id", "iglesia_id"],
            ["personas.id", "personas.iglesia_id"],
            ondelete="RESTRICT",
            name="fk_membresia_persona_iglesia",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    iglesia_id = db.Column(
        db.Integer,
        db.ForeignKey("iglesias.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    persona_id = db.Column(db.Integer, index=True)
    rol = db.Column(db.String(20), nullable=False, default="usuario", index=True)
    estado = db.Column(db.String(20), nullable=False, default="pendiente", index=True)
    fecha_solicitud = db.Column(db.DateTime, nullable=False, default=datetime.now)
    fecha_aprobacion = db.Column(db.DateTime)
    aprobado_por_id = db.Column(
        db.Integer, db.ForeignKey("usuarios.id", ondelete="SET NULL"), index=True
    )
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=datetime.now)
    fecha_actualizacion = db.Column(
        db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    usuario = db.relationship(
        "Usuario", back_populates="membresias", foreign_keys=[usuario_id]
    )
    iglesia = db.relationship(
        "Iglesia", back_populates="membresias", overlaps="persona,membresia"
    )
    persona = db.relationship(
        "Persona",
        back_populates="membresia",
        overlaps="iglesia,membresias",
        foreign_keys=[persona_id],
    )
    aprobado_por = db.relationship("Usuario", foreign_keys=[aprobado_por_id])

    @property
    def is_admin(self):
        return self.rol == "admin"

    @property
    def is_regular_user(self):
        return self.rol == "usuario"

    @property
    def grants_access(self):
        return self.estado == "activo" and self.iglesia.activa


class RegistroAuditoria(db.Model):
    __tablename__ = "registros_auditoria"

    id = db.Column(db.Integer, primary_key=True)
    iglesia_id = db.Column(
        db.Integer,
        db.ForeignKey("iglesias.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    actor_usuario_id = db.Column(
        db.Integer, db.ForeignKey("usuarios.id", ondelete="SET NULL"), index=True
    )
    accion = db.Column(db.String(80), nullable=False, index=True)
    entidad = db.Column(db.String(80), nullable=False, index=True)
    entidad_id = db.Column(db.Integer)
    detalles = db.Column(db.Text)
    fecha_hora = db.Column(
        db.DateTime, nullable=False, default=datetime.now, index=True
    )

    iglesia = db.relationship("Iglesia")
    actor = db.relationship("Usuario")
