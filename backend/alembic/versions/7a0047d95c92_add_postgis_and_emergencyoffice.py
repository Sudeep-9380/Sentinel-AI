"""Add PostGIS and EmergencyOffice

Revision ID: 7a0047d95c92
Revises: 30fe41f45609
Create Date: 2026-04-28 09:40:29.613369

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7a0047d95c92'
down_revision: Union[str, None] = '30fe41f45609'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('emergency_offices',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('office_type', sa.String(length=64), nullable=False),
    sa.Column('latitude', sa.Float(), nullable=False),
    sa.Column('longitude', sa.Float(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_emergency_offices'))
    )
    op.create_index(op.f('ix_emergency_offices_office_type'), 'emergency_offices', ['office_type'], unique=False)
    op.add_column('incidents', sa.Column('dispatched_offices', postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('incidents', 'dispatched_offices')
    op.drop_index(op.f('ix_emergency_offices_office_type'), table_name='emergency_offices')
    op.drop_table('emergency_offices')
