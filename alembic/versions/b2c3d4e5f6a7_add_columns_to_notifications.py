"""add columns to notifications table

Revision ID: b2c3d4e5f6a7
Revises: 444b0316a32d
Create Date: 2026-04-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'b2a1ef64b3f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Inspect existing columns so we only add what's missing
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_cols = {col['name'] for col in inspector.get_columns('notifications')}

    if 'title' not in existing_cols:
        op.add_column('notifications', sa.Column('title', sa.String(), nullable=False, server_default=''))
        op.alter_column('notifications', 'title', server_default=None)

    if 'message' not in existing_cols:
        op.add_column('notifications', sa.Column('message', sa.Text(), nullable=False, server_default=''))
        op.alter_column('notifications', 'message', server_default=None)

    if 'type' not in existing_cols:
        op.add_column('notifications', sa.Column('type', sa.String(), nullable=False, server_default='info'))
        op.alter_column('notifications', 'type', server_default=None)

    if 'link' not in existing_cols:
        op.add_column('notifications', sa.Column('link', sa.String(), nullable=True))

    if 'is_read' not in existing_cols:
        op.add_column('notifications', sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'))
        op.alter_column('notifications', 'is_read', server_default=None)

    if 'read_at' not in existing_cols:
        op.add_column('notifications', sa.Column('read_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('notifications', 'read_at')
    op.drop_column('notifications', 'is_read')
    op.drop_column('notifications', 'link')
    op.drop_column('notifications', 'type')
    op.drop_column('notifications', 'message')
    op.drop_column('notifications', 'title')
