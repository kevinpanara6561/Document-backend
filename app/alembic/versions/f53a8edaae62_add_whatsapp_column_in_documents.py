"""add whatsapp column in documents

Revision ID: f53a8edaae62
Revises: e7a82acb25f6
Create Date: 2024-09-05 08:16:00.694608

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f53a8edaae62'
down_revision = 'e7a82acb25f6'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('documents', sa.Column('is_whatsapp', sa.Boolean(), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('documents', 'is_whatsapp')
    # ### end Alembic commands ###
