"""update_existing_jobs_logo

Revision ID: update_existing_jobs_logo
Revises: cdb0771053c6
Create Date: 2025-04-11 16:15:09.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'update_existing_jobs_logo'
down_revision = 'cdb0771053c6'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        UPDATE job 
        SET company_logo = 'img/company_logos/default.png' 
        WHERE company_logo IS NULL
    """)


def downgrade():
    op.execute("""
        UPDATE job 
        SET company_logo = NULL 
        WHERE company_logo = 'img/company_logos/default.png'
    """)
