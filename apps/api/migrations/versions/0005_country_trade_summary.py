"""Materialize the small country-level trade summary used by the public dashboard."""

from alembic import op


revision = "0005_country_trade_summary"
down_revision = "0004_country_opportunity_indexes"
branch_labels = None
depends_on = None


def upgrade():
    # The dashboard previously grouped millions of raw observations on every request.
    # This view contains only country × year × partner rows (around one thousand rows).
    op.execute(
        """
        CREATE MATERIALIZED VIEW country_trade_yearly AS
        SELECT
            trade_observations.reporter_iso3,
            trade_observations.period_year,
            trade_observations.partner_iso3,
            SUM(trade_observations.trade_value_usd) AS trade_value_usd,
            COUNT(trade_observations.id) AS hs_count
        FROM trade_observations
        JOIN source_snapshots
          ON source_snapshots.id = trade_observations.source_snapshot_id
        WHERE (
            source_snapshots.source_identifier LIKE 'local:%'
            OR source_snapshots.source_type = 'FIXTURE'
        )
          AND trade_observations.partner_iso3 IN ('CHN', 'WLD')
          AND trade_observations.flow = 'IMPORT'
          AND trade_observations.period_type = 'YEAR'
        GROUP BY
            trade_observations.reporter_iso3,
            trade_observations.period_year,
            trade_observations.partner_iso3
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX ix_country_trade_yearly_lookup
          ON country_trade_yearly (reporter_iso3, period_year, partner_iso3)
        """
    )


def downgrade():
    op.execute("DROP MATERIALIZED VIEW IF EXISTS country_trade_yearly")
