"""Adding uuid_ossp

Revision ID: 516f2e855bc2
Revises: 
Create Date: 2022-03-14 01:04:42.788018

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '516f2e855bc2'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')


def downgrade():
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp";')
