"""Agrega fecha de nacimiento opcional a personas.

Revision ID: c73b89c1e2a4
Revises: 8de9dc5a35bd
"""

from alembic import op
import sqlalchemy as sa

revision = "c73b89c1e2a4"
down_revision = "8de9dc5a35bd"
branch_labels = None
depends_on = None


def upgrade():
    """Añade la fecha sin modificar registros existentes."""
    op.add_column(
        "personas", sa.Column("fecha_nacimiento", sa.Date(), nullable=True)
    )


def downgrade():
    """Retira únicamente la columna agregada por esta revisión."""
    op.drop_column("personas", "fecha_nacimiento")
