"""Agrega aislamiento multiiglesia y conserva todos los registros existentes.

Revision ID: 8de9dc5a35bd
Revises: 94cbf9c198f1
Create Date: 2026-08-04
"""

from alembic import context, op
import sqlalchemy as sa


revision = "8de9dc5a35bd"
down_revision = "94cbf9c198f1"
branch_labels = None
depends_on = None


def _drop_single_column_foreign_keys(table_name, column_name):
    if context.is_offline_mode():
        known_names = {
            ("asistencias", "persona_id"): "fk_asistencia_persona",
            ("asistencias", "evento_id"): "fk_asistencia_evento",
            ("usuarios", "persona_id"): "fk_usuario_persona",
        }
        op.drop_constraint(
            known_names[(table_name, column_name)], table_name, type_="foreignkey"
        )
        return
    inspector = sa.inspect(op.get_bind())
    for foreign_key in inspector.get_foreign_keys(table_name):
        if foreign_key.get("constrained_columns") == [column_name] and foreign_key.get(
            "name"
        ):
            op.drop_constraint(foreign_key["name"], table_name, type_="foreignkey")


def _drop_unique_index_for_columns(table_name, columns):
    if context.is_offline_mode():
        op.drop_index("codigo", table_name="personas")
        return
    inspector = sa.inspect(op.get_bind())
    for index in inspector.get_indexes(table_name):
        if index.get("unique") and index.get("column_names") == columns:
            op.drop_index(index["name"], table_name=table_name)
            return
    for constraint in inspector.get_unique_constraints(table_name):
        if constraint.get("column_names") == columns and constraint.get("name"):
            op.drop_constraint(constraint["name"], table_name, type_="unique")
            return


def upgrade():
    op.create_table(
        "iglesias",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("descripcion", sa.String(500)),
        sa.Column("ciudad", sa.String(120)),
        sa.Column("pais", sa.String(80), nullable=False, server_default="Guatemala"),
        sa.Column(
            "zona_horaria",
            sa.String(80),
            nullable=False,
            server_default="America/Guatemala",
        ),
        sa.Column("logo_url", sa.String(500)),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "fecha_actualizacion",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_iglesias_slug", "iglesias", ["slug"], unique=True)
    op.create_index("ix_iglesias_activa", "iglesias", ["activa"])

    op.execute(
        "INSERT INTO iglesias "
        "(nombre, slug, pais, zona_horaria, activa, fecha_creacion, fecha_actualizacion) "
        "VALUES ('Iglesia Principal', 'iglesia-principal', 'Guatemala', "
        "'America/Guatemala', TRUE, NOW(), NOW())"
    )
    bind = op.get_bind()

    tenant_updates = {
        "personas": "UPDATE personas SET iglesia_id = (SELECT id FROM iglesias WHERE slug = 'iglesia-principal') WHERE iglesia_id IS NULL",
        "eventos": "UPDATE eventos SET iglesia_id = (SELECT id FROM iglesias WHERE slug = 'iglesia-principal') WHERE iglesia_id IS NULL",
        "asistencias": "UPDATE asistencias SET iglesia_id = (SELECT id FROM iglesias WHERE slug = 'iglesia-principal') WHERE iglesia_id IS NULL",
    }
    for table_name, update_sql in tenant_updates.items():
        op.add_column(table_name, sa.Column("iglesia_id", sa.Integer(), nullable=True))
        op.create_index(f"ix_{table_name}_iglesia_id", table_name, ["iglesia_id"])
        op.execute(update_sql)

    if not context.is_offline_mode():
        missing = sum(
            bind.execute(
                sa.text(f"SELECT COUNT(*) FROM {table_name} WHERE iglesia_id IS NULL")
            ).scalar_one()
            for table_name in ("personas", "eventos", "asistencias")
        )
        if missing:
            raise RuntimeError(
                "La migración detectó registros sin iglesia y fue detenida."
            )

    _drop_unique_index_for_columns("personas", ["codigo"])
    _drop_single_column_foreign_keys("asistencias", "persona_id")
    _drop_single_column_foreign_keys("asistencias", "evento_id")

    op.create_unique_constraint(
        "uq_persona_iglesia_codigo", "personas", ["iglesia_id", "codigo"]
    )
    op.create_unique_constraint(
        "uq_persona_id_iglesia", "personas", ["id", "iglesia_id"]
    )
    op.create_unique_constraint("uq_evento_id_iglesia", "eventos", ["id", "iglesia_id"])
    op.create_foreign_key(
        "fk_persona_iglesia",
        "personas",
        "iglesias",
        ["iglesia_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_evento_iglesia",
        "eventos",
        "iglesias",
        ["iglesia_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_asistencia_iglesia",
        "asistencias",
        "iglesias",
        ["iglesia_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_asistencia_persona_iglesia",
        "asistencias",
        "personas",
        ["persona_id", "iglesia_id"],
        ["id", "iglesia_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_asistencia_evento_iglesia",
        "asistencias",
        "eventos",
        ["evento_id", "iglesia_id"],
        ["id", "iglesia_id"],
        ondelete="CASCADE",
    )

    for table_name in ("personas", "eventos", "asistencias"):
        op.alter_column(
            table_name, "iglesia_id", existing_type=sa.Integer(), nullable=False
        )

    op.create_table(
        "membresias_iglesia",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("iglesia_id", sa.Integer(), nullable=False),
        sa.Column("persona_id", sa.Integer()),
        sa.Column("rol", sa.String(20), nullable=False, server_default="usuario"),
        sa.Column("estado", sa.String(20), nullable=False, server_default="pendiente"),
        sa.Column(
            "fecha_solicitud",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("fecha_aprobacion", sa.DateTime()),
        sa.Column("aprobado_por_id", sa.Integer()),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "fecha_actualizacion",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("rol IN ('usuario', 'admin')", name="ck_membresia_rol"),
        sa.CheckConstraint(
            "estado IN ('pendiente', 'activo', 'suspendido', 'rechazado')",
            name="ck_membresia_estado",
        ),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["iglesia_id"], ["iglesias.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["aprobado_por_id"], ["usuarios.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["persona_id", "iglesia_id"],
            ["personas.id", "personas.iglesia_id"],
            ondelete="RESTRICT",
            name="fk_membresia_persona_iglesia",
        ),
        sa.UniqueConstraint(
            "usuario_id", "iglesia_id", name="uq_membresia_usuario_iglesia"
        ),
        sa.UniqueConstraint(
            "iglesia_id", "persona_id", name="uq_membresia_iglesia_persona"
        ),
    )
    for column in (
        "usuario_id",
        "iglesia_id",
        "persona_id",
        "rol",
        "estado",
        "aprobado_por_id",
    ):
        op.create_index(
            f"ix_membresias_iglesia_{column}", "membresias_iglesia", [column]
        )

    op.execute(
        "INSERT INTO membresias_iglesia "
        "(usuario_id, iglesia_id, persona_id, rol, estado, fecha_solicitud, "
        "fecha_aprobacion, fecha_creacion, fecha_actualizacion) "
        "SELECT id, (SELECT id FROM iglesias WHERE slug = 'iglesia-principal'), "
        "persona_id, rol, 'activo', fecha_creacion, NOW(), fecha_creacion, "
        "fecha_actualizacion FROM usuarios"
    )

    _drop_single_column_foreign_keys("usuarios", "persona_id")
    if context.is_offline_mode():
        op.drop_index("ix_usuarios_persona_id", table_name="usuarios")
        op.drop_index("ix_usuarios_rol", table_name="usuarios")
        op.drop_constraint("ck_usuario_rol", "usuarios", type_="check")
    else:
        inspector = sa.inspect(bind)
        for index in inspector.get_indexes("usuarios"):
            if index["name"] in {"ix_usuarios_persona_id", "ix_usuarios_rol"}:
                op.drop_index(index["name"], table_name="usuarios")
        for check in inspector.get_check_constraints("usuarios"):
            if check.get("name") == "ck_usuario_rol":
                op.drop_constraint("ck_usuario_rol", "usuarios", type_="check")
    op.drop_column("usuarios", "persona_id")
    op.drop_column("usuarios", "rol")

    op.create_table(
        "registros_auditoria",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("iglesia_id", sa.Integer(), nullable=False),
        sa.Column("actor_usuario_id", sa.Integer()),
        sa.Column("accion", sa.String(80), nullable=False),
        sa.Column("entidad", sa.String(80), nullable=False),
        sa.Column("entidad_id", sa.Integer()),
        sa.Column("detalles", sa.Text()),
        sa.Column(
            "fecha_hora", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["iglesia_id"], ["iglesias.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["actor_usuario_id"], ["usuarios.id"], ondelete="SET NULL"
        ),
    )
    for column in ("iglesia_id", "actor_usuario_id", "accion", "entidad", "fecha_hora"):
        op.create_index(
            f"ix_registros_auditoria_{column}", "registros_auditoria", [column]
        )


def downgrade():
    op.add_column(
        "usuarios",
        sa.Column("rol", sa.String(20), nullable=False, server_default="usuario"),
    )
    op.add_column("usuarios", sa.Column("persona_id", sa.Integer(), nullable=True))
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE usuarios u JOIN membresias_iglesia m ON m.usuario_id = u.id "
            "SET u.rol = m.rol, u.persona_id = m.persona_id "
            "WHERE m.iglesia_id = (SELECT id FROM iglesias WHERE slug = 'iglesia-principal')"
        )
    )
    op.create_index("ix_usuarios_rol", "usuarios", ["rol"])
    op.create_index("ix_usuarios_persona_id", "usuarios", ["persona_id"], unique=True)
    op.create_foreign_key(
        "fk_usuario_persona",
        "usuarios",
        "personas",
        ["persona_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_usuario_rol", "usuarios", "rol IN ('usuario', 'admin')"
    )

    op.drop_table("registros_auditoria")
    op.drop_table("membresias_iglesia")

    op.drop_constraint(
        "fk_asistencia_evento_iglesia", "asistencias", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_asistencia_persona_iglesia", "asistencias", type_="foreignkey"
    )
    op.drop_constraint("fk_asistencia_iglesia", "asistencias", type_="foreignkey")
    op.drop_constraint("fk_evento_iglesia", "eventos", type_="foreignkey")
    op.drop_constraint("fk_persona_iglesia", "personas", type_="foreignkey")
    op.drop_constraint("uq_evento_id_iglesia", "eventos", type_="unique")
    op.drop_constraint("uq_persona_id_iglesia", "personas", type_="unique")
    op.drop_constraint("uq_persona_iglesia_codigo", "personas", type_="unique")
    op.create_unique_constraint("uq_persona_codigo", "personas", ["codigo"])
    op.create_foreign_key(
        "fk_asistencia_persona",
        "asistencias",
        "personas",
        ["persona_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_asistencia_evento",
        "asistencias",
        "eventos",
        ["evento_id"],
        ["id"],
        ondelete="CASCADE",
    )
    for table_name in ("asistencias", "eventos", "personas"):
        op.drop_index(f"ix_{table_name}_iglesia_id", table_name=table_name)
        op.drop_column(table_name, "iglesia_id")
    op.drop_table("iglesias")
