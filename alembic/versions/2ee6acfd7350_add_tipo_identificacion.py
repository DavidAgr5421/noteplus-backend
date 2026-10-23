"""add tipo_identificacion to estudiantes

Revision ID: 2ee6acfd7350
Revises: 3f7a1c9e2b4d
Create Date: 2026-10-09

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2ee6acfd7350'
down_revision: str | None = '3f7a1c9e2b4d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('estudiantes', sa.Column('tipo_identificacion', sa.String(length=10), nullable=False, server_default='CC'))


def downgrade() -> None:
    op.drop_column('estudiantes', 'tipo_identificacion')
