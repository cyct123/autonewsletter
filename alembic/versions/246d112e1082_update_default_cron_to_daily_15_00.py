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
    # Change column default
    op.alter_column('system_config', 'weekly_cron',
                    server_default='0 15 * * *')

    # Update existing rows that still have the old default
    op.execute("UPDATE system_config SET weekly_cron = '0 15 * * *' WHERE weekly_cron = '0 9 * * 3'")


def downgrade() -> None:
    # Restore old default
    op.alter_column('system_config', 'weekly_cron',
                    server_default='0 9 * * 3')

    # Note: We don't restore existing row values on downgrade to avoid
    # overwriting intentional user changes. Only the column default is reverted.
