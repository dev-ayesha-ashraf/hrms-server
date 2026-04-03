"""create notifications table (stub - table already exists)

Revision ID: b2a1ef64b3f3
Revises: 9cac31f56b0f
Create Date: 2026-03-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2a1ef64b3f3'
down_revision: Union[str, Sequence[str], None] = '9cac31f56b0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Table was already created in a previous migration run; this is a stub
    # to restore the lost migration file entry so the chain is intact.
    pass


def downgrade() -> None:
    pass
