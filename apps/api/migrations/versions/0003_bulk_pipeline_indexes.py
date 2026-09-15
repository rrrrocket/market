"""Add indexes required by the local bulk analysis pipeline."""

import sqlalchemy as sa
from alembic import op

revision = "0003_bulk_pipeline_indexes"
down_revision = "0002_distribution_intelligence"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    indexes = {item["name"] for item in inspector.get_indexes("trade_observations")}
    if "ix_trade_observations_source_snapshot_id" not in indexes:
        op.create_index(
            "ix_trade_observations_source_snapshot_id",
            "trade_observations",
            ["source_snapshot_id"],
        )


def downgrade():
    inspector = sa.inspect(op.get_bind())
    indexes = {item["name"] for item in inspector.get_indexes("trade_observations")}
    if "ix_trade_observations_source_snapshot_id" in indexes:
        op.drop_index(
            "ix_trade_observations_source_snapshot_id", table_name="trade_observations"
        )
