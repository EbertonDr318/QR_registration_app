"""Crea usuarios sin modificar las tablas operativas existentes.

Revision ID: 94cbf9c198f1
Revises:
Create Date: 2026-08-03 11:39:30.210032

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "94cbf9c198f1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=False),
        sa.Column("nombre", sa.String(length=160), nullable=False),
        sa.Column("foto_url", sa.String(length=500), nullable=True),
        sa.Column(
            "proveedor", sa.String(length=30), nullable=False, server_default="google"
        ),
        sa.Column("proveedor_subject", sa.String(length=255), nullable=True),
        sa.Column(
            "rol", sa.String(length=20), nullable=False, server_default="usuario"
        ),
        sa.Column("persona_id", sa.Integer(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("ultimo_acceso", sa.DateTime(), nullable=True),
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
        sa.CheckConstraint("rol IN ('usuario', 'admin')", name="ck_usuario_rol"),
        sa.ForeignKeyConstraint(
            ["persona_id"],
            ["personas.id"],
            ondelete="SET NULL",
            name="fk_usuario_persona",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_usuarios_activo", "usuarios", ["activo"], unique=False)
    op.create_index("ix_usuarios_email", "usuarios", ["email"], unique=True)
    op.create_index("ix_usuarios_persona_id", "usuarios", ["persona_id"], unique=True)
    op.create_index(
        "ix_usuarios_proveedor_subject",
        "usuarios",
        ["proveedor_subject"],
        unique=True,
    )
    op.create_index("ix_usuarios_rol", "usuarios", ["rol"], unique=False)


def downgrade():
    op.drop_index("ix_usuarios_rol", table_name="usuarios")
    op.drop_index("ix_usuarios_persona_id", table_name="usuarios")
    op.drop_index("ix_usuarios_proveedor_subject", table_name="usuarios")
    op.drop_index("ix_usuarios_email", table_name="usuarios")
    op.drop_index("ix_usuarios_activo", table_name="usuarios")
    op.drop_table("usuarios")
