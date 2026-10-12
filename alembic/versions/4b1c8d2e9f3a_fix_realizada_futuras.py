"""fix realizada en clases futuras (solo el dia pasado puede estar realizada)

Revision ID: 4b1c8d2e9f3a
Revises: 2ee6acfd7350
Create Date: 2026-10-10

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '4b1c8d2e9f3a'
down_revision: Union[str, None] = '2ee6acfd7350'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Las clases con fecha futura no pueden estar realizadas (antes nacían todas en true)
    op.execute(
        """
        UPDATE clases
        SET realizada = false
        WHERE fecha > CURRENT_DATE AND realizada = true
        """
    )


def downgrade() -> None:
    # Sin reversa de datos: no se puede saber cuáles fueron marcadas a mano
    pass
