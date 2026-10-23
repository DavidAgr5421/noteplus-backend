"""add trimestre to fichas

Revision ID: 3f7a1c9e2b4d
Revises: e9eb83347c8c
Create Date: 2026-10-09

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '3f7a1c9e2b4d'
down_revision: str | None = 'e9eb83347c8c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('fichas', sa.Column('trimestre', sa.String(length=20), nullable=False, server_default=''))
    # Backfill existente: T1–T4 + año desde fecha_inicio
    op.execute(
        """
        UPDATE fichas
        SET trimestre = 'T' || ((EXTRACT(MONTH FROM fecha_inicio)::int - 1) / 3 + 1)::int || ' ' || EXTRACT(YEAR FROM fecha_inicio)::int
        WHERE trimestre = ''
        """
    )


def downgrade() -> None:
    op.drop_column('fichas', 'trimestre')
