"""Add provider-aware demand and distribution intelligence foundations."""

import sqlalchemy as sa
from alembic import op

from app.core.database import Base
from app.models import *  # noqa: F403

revision = "0002_distribution_intelligence"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


NEW_TABLES = [
    "data_sources",
    "hs_classifications",
    "hs_correspondence",
    "product_entities",
    "product_identifiers",
    "product_hs_mappings",
    "product_relationships",
    "demand_signals",
    "marketplace_signals",
    "explicit_demands",
    "market_access_metrics",
    "country_metrics",
    "supply_fit",
    "distribution_economics",
    "opportunity_risks",
    "watchlists",
    "opportunity_events",
    "opportunity_outcomes",
    "decision_recommendations",
    "distribution_plans",
    "metric_definitions",
    "data_jobs",
]


ADDITIONS = {
    "source_snapshots": [
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("data_sources.id"), nullable=True),
        sa.Column("source_revision", sa.String(120), nullable=True),
    ],
    "trade_observations": [
        sa.Column("period_type", sa.String(20), nullable=True, server_default="YEAR"),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
    ],
    "market_opportunities": [
        sa.Column("product_scope_type", sa.String(20), nullable=True, server_default="HS"),
        sa.Column("product_scope_id", sa.String(120), nullable=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("product_entities.id"), nullable=True),
        sa.Column("channel", sa.String(80), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("structural_demand_score", sa.Float(), nullable=True),
        sa.Column("digital_demand_score", sa.Float(), nullable=True),
        sa.Column("marketplace_demand_score", sa.Float(), nullable=True),
        sa.Column("explicit_demand_score", sa.Float(), nullable=True),
        sa.Column("market_access_score", sa.Float(), nullable=True),
        sa.Column("country_capacity_score", sa.Float(), nullable=True),
        sa.Column("supply_fit_score", sa.Float(), nullable=True),
        sa.Column("economics_score", sa.Float(), nullable=True),
        sa.Column("competition_score", sa.Float(), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("distribution_opportunity_score", sa.Float(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
    ],
    "evidence": [
        sa.Column("value_numeric", sa.Float(), nullable=True),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("value_json", sa.JSON(), nullable=True),
        sa.Column("unit", sa.String(40), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("data_sources.id"), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_reliability", sa.String(20), nullable=True, server_default="A"),
        sa.Column("observed_type", sa.String(20), nullable=True, server_default="REPORTED"),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column(
            "raw_snapshot_id", sa.Integer(), sa.ForeignKey("source_snapshots.id"), nullable=True
        ),
        sa.Column("confidence", sa.Float(), nullable=True),
    ],
}


def upgrade():
    bind = op.get_bind()
    for table_name in NEW_TABLES:
        Base.metadata.tables[table_name].create(bind=bind, checkfirst=True)

    inspector = sa.inspect(bind)
    for table_name, columns in ADDITIONS.items():
        existing = {column["name"] for column in inspector.get_columns(table_name)}
        for column in columns:
            if column.name not in existing:
                op.add_column(table_name, column)

    op.execute("UPDATE trade_observations SET period_type = 'YEAR' WHERE period_type IS NULL")
    op.execute(
        "UPDATE market_opportunities SET product_scope_type = 'HS', product_scope_id = hs_code WHERE product_scope_type IS NULL OR product_scope_id IS NULL"
    )
    op.execute(
        "UPDATE evidence SET source_reliability = 'A', observed_type = 'REPORTED' WHERE source_reliability IS NULL OR observed_type IS NULL"
    )

    uniques = sa.inspect(bind).get_unique_constraints("trade_observations")
    target_columns = {
        "classification",
        "hs_code",
        "period_type",
        "period_start",
        "reporter_iso3",
        "partner_iso3",
        "flow",
    }
    if not any(set(item["column_names"]) == target_columns for item in uniques):
        old_columns = {
            "classification",
            "hs_code",
            "period_year",
            "reporter_iso3",
            "partner_iso3",
            "flow",
        }
        old = next((item for item in uniques if set(item["column_names"]) == old_columns), None)
        with op.batch_alter_table("trade_observations") as batch:
            if old and old.get("name"):
                batch.drop_constraint(old["name"], type_="unique")
            batch.create_unique_constraint(
                "uq_trade_observation_period",
                [
                    "classification",
                    "hs_code",
                    "period_type",
                    "period_start",
                    "reporter_iso3",
                    "partner_iso3",
                    "flow",
                ],
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table_name, columns in reversed(list(ADDITIONS.items())):
        existing = {column["name"] for column in inspector.get_columns(table_name)}
        for column in reversed(columns):
            if column.name in existing:
                op.drop_column(table_name, column.name)
    for table_name in reversed(NEW_TABLES):
        Base.metadata.tables[table_name].drop(bind=bind, checkfirst=True)
