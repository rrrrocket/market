"""Add indexes for country-level opportunity analysis."""

import sqlalchemy as sa
from alembic import op

revision = "0004_country_opportunity_indexes"
down_revision = "0003_bulk_pipeline_indexes"
branch_labels = None
depends_on = None


def _index_names(table_name: str) -> set[str]:
    return {item["name"] for item in sa.inspect(op.get_bind()).get_indexes(table_name)}


def upgrade():
    if "ix_trade_observations_country_partner_period" not in _index_names(
        "trade_observations"
    ):
        op.create_index(
            "ix_trade_observations_country_partner_period",
            "trade_observations",
            ["reporter_iso3", "partner_iso3", "flow", "period_type", "period_year"],
        )
    if "ix_market_metrics_origin_year_country" not in _index_names("market_metrics"):
        op.create_index(
            "ix_market_metrics_origin_year_country",
            "market_metrics",
            ["origin_iso3", "period_year", "country_iso3"],
        )


def downgrade():
    if "ix_market_metrics_origin_year_country" in _index_names("market_metrics"):
        op.drop_index(
            "ix_market_metrics_origin_year_country", table_name="market_metrics"
        )
    if "ix_trade_observations_country_partner_period" in _index_names(
        "trade_observations"
    ):
        op.drop_index(
            "ix_trade_observations_country_partner_period",
            table_name="trade_observations",
        )
