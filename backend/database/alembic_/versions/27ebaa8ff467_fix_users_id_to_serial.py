"""fix_users_id_to_serial

Revision ID: 27ebaa8ff467
Revises: 4378b797e0a0
Create Date: 2025-08-25 10:53:33.923736

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '27ebaa8ff467'
down_revision: Union[str, None] = '4378b797e0a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sequence for users.id if it doesn't exist
    op.execute("CREATE SEQUENCE IF NOT EXISTS users_id_seq OWNED BY users.id")
    
    # Set the sequence to start from the current max id + 1
    op.execute("""
        SELECT setval('users_id_seq', COALESCE((SELECT MAX(id) FROM users), 0) + 1, false)
    """)
    
    # Set the default value for id column to use the sequence
    op.execute("ALTER TABLE users ALTER COLUMN id SET DEFAULT nextval('users_id_seq')")
    
    # Update existing NULL id values (if any)
    op.execute("""
        UPDATE users SET id = nextval('users_id_seq') WHERE id IS NULL
    """)


def downgrade() -> None:
    # Remove the default value
    op.execute("ALTER TABLE users ALTER COLUMN id DROP DEFAULT")
    
    # Drop the sequence
    op.execute("DROP SEQUENCE IF EXISTS users_id_seq")
