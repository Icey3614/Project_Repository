"""relax tickets session_seat unique

Revision ID: 70d75a2dca46
Revises: b02b70a5f859
Create Date: 2026-08-18 13:17:45.483558

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '70d75a2dca46'
down_revision: Union[str, None] = 'b02b70a5f859'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 先建普通索引供外键使用，再删除唯一索引（MySQL 1553 约束）
    op.create_index(
        op.f('ix_tickets_session_seat_id'),
        'tickets',
        ['session_seat_id'],
        unique=False,
    )
    op.drop_index(op.f('session_seat_id'), table_name='tickets')


def downgrade() -> None:
    op.create_index(op.f('session_seat_id'), 'tickets', ['session_seat_id'], unique=True)
    op.drop_index(op.f('ix_tickets_session_seat_id'), table_name='tickets')
