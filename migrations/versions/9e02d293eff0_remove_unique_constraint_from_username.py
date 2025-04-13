"""Remove unique constraint from username

Revision ID: 9e02d293eff0
Revises: update_existing_jobs_logo
Create Date: 2025-04-12 15:01:17.721321

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9e02d293eff0'
down_revision = 'update_existing_jobs_logo'
branch_labels = None
depends_on = None


def upgrade():
    # SQLite doesn't support dropping constraints directly
    # We need to recreate the table without the constraint
    
    # Create a temporary table with the new schema
    op.execute('PRAGMA foreign_keys=off')
    
    # Create a new table without the unique constraint on username
    op.execute('''
        CREATE TABLE user_new (
            id INTEGER NOT NULL PRIMARY KEY,
            username VARCHAR(80) NOT NULL,
            email VARCHAR(120) NOT NULL UNIQUE,
            password VARCHAR(120) NOT NULL,
            role VARCHAR(20) NOT NULL,
            profile_picture VARCHAR(200)
        )
    ''')
    
    # Copy data from the old table to the new one
    op.execute('''
        INSERT INTO user_new 
        SELECT id, username, email, password, role, profile_picture
        FROM user
    ''')
    
    # Drop the old table and rename the new one
    op.execute('DROP TABLE user')
    op.execute('ALTER TABLE user_new RENAME TO user')
    
    # Re-create indexes and foreign keys if needed
    # This depends on your specific schema
    
    op.execute('PRAGMA foreign_keys=on')


def downgrade():
    # Revert by adding the unique constraint back
    op.execute('PRAGMA foreign_keys=off')
    
    # Create a new table with the unique constraint on username
    op.execute('''
        CREATE TABLE user_new (
            id INTEGER NOT NULL PRIMARY KEY,
            username VARCHAR(80) NOT NULL UNIQUE,
            email VARCHAR(120) NOT NULL UNIQUE,
            password VARCHAR(120) NOT NULL,
            role VARCHAR(20) NOT NULL,
            profile_picture VARCHAR(200)
        )
    ''')
    
    # Copy data from the old table to the new one
    op.execute('''
        INSERT INTO user_new 
        SELECT id, username, email, password, role, profile_picture
        FROM user
    ''')
    
    # Drop the old table and rename the new one
    op.execute('DROP TABLE user')
    op.execute('ALTER TABLE user_new RENAME TO user')
    
    # Re-create indexes and foreign keys if needed
    
    op.execute('PRAGMA foreign_keys=on')
