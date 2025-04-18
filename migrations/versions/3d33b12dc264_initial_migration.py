"""Initial migration.

Revision ID: 3d33b12dc264
Revises: 
Create Date: 2025-04-10 07:06:19.301737

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3d33b12dc264'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('application', schema=None) as batch_op:
        batch_op.add_column(sa.Column('resume_path', sa.String(length=200), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('application', schema=None) as batch_op:
        batch_op.drop_column('resume_path')

    # ### end Alembic commands ###
