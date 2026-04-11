"""update default cron to daily 15:00

Revision ID: 246d112e1082
Revises: 51ef90c15388
Create Date: 2026-04-11 22:24:04.942782

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '246d112e1082'
down_revision = '51ef90c15388'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Change column default for new rows
    op.alter_column('system_config', 'weekly_cron',
                    server_default='0 15 * * *')

    # Note: We don't update existing rows to preserve user's chosen schedule.
    # Existing installations will keep their current cron expression.


def downgrade() -> None:
    # Restore old default
    op.alter_column('system_config', 'weekly_cron',
                    server_default='0 9 * * 3')

    # Note: We don't restore existing row values on downgrade to avoid
    # overwriting intentional user changes. Only the column default is reverted.
