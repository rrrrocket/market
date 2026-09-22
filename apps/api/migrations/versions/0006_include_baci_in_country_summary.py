"""Include BACI aggregates in the country dashboard materialized view."""

from alembic import op

revision = "0006_baci_summary"
down_revision = "0005_country_trade_summary"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DROP MATERIALIZED VIEW country_trade_yearly")
    op.execute("""
        CREATE MATERIALIZED VIEW country_trade_yearly AS
        SELECT t.reporter_iso3, t.period_year, t.partner_iso3,
               SUM(t.trade_value_usd) AS trade_value_usd, COUNT(t.id) AS hs_count
        FROM trade_observations t JOIN source_snapshots s ON s.id=t.source_snapshot_id
        WHERE (s.source_identifier LIKE 'local:%' OR s.source_identifier LIKE 'baci:%' OR s.source_type='FIXTURE')
          AND t.partner_iso3 IN ('CHN','WLD') AND t.flow='IMPORT' AND t.period_type='YEAR'
        GROUP BY t.reporter_iso3, t.period_year, t.partner_iso3
    """)
    op.execute("CREATE UNIQUE INDEX ix_country_trade_yearly_lookup ON country_trade_yearly (reporter_iso3, period_year, partner_iso3)")


def downgrade():
    pass
