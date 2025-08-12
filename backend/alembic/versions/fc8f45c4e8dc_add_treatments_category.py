"""add_treatments_category

Revision ID: fc8f45c4e8dc
Revises: 39ec29f00e94
Create Date: 2025-08-11 00:34:41.838066

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fc8f45c4e8dc'
down_revision: Union[str, None] = '39ec29f00e94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the treatments category for respiratory and medical treatments
    from datetime import datetime
    now = datetime.utcnow()
    
    # Create a connection to insert the new category
    connection = op.get_bind()
    
    # Insert the treatments category
    connection.execute(sa.text("""
        INSERT INTO care_task_category (name, description, color, is_default, active, created_at, updated_at)
        VALUES (:name, :description, :color, :is_default, true, :created_at, :updated_at)
    """), {
        'name': 'treatments',
        'description': 'Medical treatments like nebulizer, cough assist, breathing exercises, and other therapeutic interventions',
        'color': '#f39c12',  # Orange color for treatments
        'is_default': True,
        'created_at': now,
        'updated_at': now
    })


def downgrade() -> None:
    # Remove the treatments category
    connection = op.get_bind()
    connection.execute(sa.text("""
        DELETE FROM care_task_category WHERE name = 'treatments' AND is_default = true
    """))
