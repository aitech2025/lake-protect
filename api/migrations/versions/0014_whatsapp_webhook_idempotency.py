"""Record provider message IDs so WhatsApp webhook retries are safe.

Revision ID: 0014
Revises: 0013
"""
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

UP = r"""
ALTER TABLE citizen_messages ADD COLUMN provider_message_id text;
CREATE UNIQUE INDEX citizen_messages_provider_message_once
    ON citizen_messages (provider_message_id) WHERE provider_message_id IS NOT NULL;
"""

DOWN = r"""
DROP INDEX citizen_messages_provider_message_once;
ALTER TABLE citizen_messages DROP COLUMN provider_message_id;
"""


def upgrade() -> None:
    op.execute(UP)


def downgrade() -> None:
    op.execute(DOWN)
