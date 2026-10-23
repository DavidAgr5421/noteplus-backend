"""add contacto to estudiantes

Revision ID: 5c2d9e1a4b7f
Revises: 4b1c8d2e9f3a
Create Date: 2026-10-12

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5c2d9e1a4b7f'
down_revision: str | None = '4b1c8d2e9f3a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('estudiantes', sa.Column('contacto', sa.String(length=320), nullable=True))


def downgrade() -> None:
    op.drop_column('estudiantes', 'contacto')
