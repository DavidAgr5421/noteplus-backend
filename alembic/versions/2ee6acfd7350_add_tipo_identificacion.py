"""add tipo_identificacion to estudiantes

Revision ID: 2ee6acfd7350
Revises: 3f7a1c9e2b4d
Create Date: 2026-10-09

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2ee6acfd7350'
down_revision: Union[str, None] = '3f7a1c9e2b4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('estudiantes', sa.Column('tipo_identificacion', sa.String(length=10), nullable=False, server_default='CC'))


def downgrade() -> None:
    op.drop_column('estudiantes', 'tipo_identificacion')
