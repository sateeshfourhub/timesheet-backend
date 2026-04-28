"""add superuser and future access

Revision ID: c3d4e5f6a7b8
Revises: 4602bd233158
Create Date: 2026-04-28 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = '4602bd233158'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('future_time_log_enabled', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('users', 'future_time_log_enabled')
    op.drop_column('users', 'is_superuser')
