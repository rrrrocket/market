import enum
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def now() -> datetime:
    return datetime.now(UTC)


class AnalysisStatus(enum.StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class SourceReliability(enum.StrEnum):
    A_PLUS = "A_PLUS"
    A = "A"
    A_MINUS = "A_MINUS"
    B_PLUS = "B_PLUS"
    B = "B"
    C = "C"
    D = "D"


class ObservedType(enum.StrEnum):
    REPORTED = "REPORTED"
    OBSERVED = "OBSERVED"
    ESTIMATED = "ESTIMATED"
    INFERRED = "INFERRED"
    AI_GENERATED = "AI_GENERATED"


class FreshnessStatus(enum.StrEnum):
    FRESH = "FRESH"
    AGING = "AGING"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class PeriodType(enum.StrEnum):
    YEAR = "YEAR"
    QUARTER = "QUARTER"
    MONTH = "MONTH"
    WEEK = "WEEK"
    DAY = "DAY"


class Country(Base):
    __tablename__ = "countries"
    id: Mapped[int] = mapped_column(primary_key=True)
    iso2: Mapped[str] = mapped_column(String(2), unique=True)
    iso3: Mapped[str] = mapped_column(String(3), unique=True, index=True)
    numeric_code: Mapped[str | None] = mapped_column(String(3))
    name_en: Mapped[str] = mapped_column(String(120))
    name_zh: Mapped[str | None] = mapped_column(String(120))
    region: Mapped[str | None] = mapped_column(String(80))
    subregion: Mapped[str | None] = mapped_column(String(80))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class HsProduct(Base):
    __tablename__ = "hs_products"
    __table_args__ = (UniqueConstraint("classification", "hs_code"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    classification: Mapped[str] = mapped_column(String(20), default="HS2022")
    hs_code: Mapped[str] = mapped_column(String(10), index=True)
    level: Mapped[int] = mapped_column(Integer)
    parent_code: Mapped[str | None] = mapped_column(String(10))
    name_en: Mapped[str] = mapped_column(String(500))
    name_zh: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class SourceSnapshot(Base):
    __tablename__ = "source_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(40), index=True)
    source_identifier: Mapped[str] = mapped_column(String(300), index=True)
    request_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    response_payload: Mapped[dict | list] = mapped_column(JSON)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    checksum: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="SUCCESS")
    error_message: Mapped[str | None] = mapped_column(Text)
    source_revision: Mapped[str | None] = mapped_column(String(120))


class TradeObservation(Base):
    __tablename__ = "trade_observations"
    __table_args__ = (
        UniqueConstraint(
            "classification",
            "hs_code",
            "period_type",
            "period_start",
            "reporter_iso3",
            "partner_iso3",
            "flow",
            name="uq_trade_observation_period",
        ),
        Index(
            "ix_trade_observations_country_partner_period",
            "reporter_iso3",
            "partner_iso3",
            "flow",
            "period_type",
            "period_year",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    classification: Mapped[str] = mapped_column(String(20), default="HS2022")
    hs_code: Mapped[str] = mapped_column(String(10), index=True)
    period_year: Mapped[int] = mapped_column(Integer, index=True)
    period_type: Mapped[str] = mapped_column(String(20), default=PeriodType.YEAR.value)
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    reporter_iso3: Mapped[str] = mapped_column(String(3), index=True)
    partner_iso3: Mapped[str] = mapped_column(String(3), index=True)
    flow: Mapped[str] = mapped_column(String(10))
    trade_value_usd: Mapped[float] = mapped_column(Float)
    net_weight_kg: Mapped[float | None] = mapped_column(Float)
    quantity: Mapped[float | None] = mapped_column(Float)
    quantity_unit: Mapped[str | None] = mapped_column(String(40))
    source_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("source_snapshots.id"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MarketMetric(Base):
    __tablename__ = "market_metrics"
    __table_args__ = (
        UniqueConstraint("hs_code", "country_iso3", "origin_iso3", "period_year"),
        Index(
            "ix_market_metrics_origin_year_country",
            "origin_iso3",
            "period_year",
            "country_iso3",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    hs_code: Mapped[str] = mapped_column(String(10), index=True)
    country_iso3: Mapped[str] = mapped_column(String(3), index=True)
    origin_iso3: Mapped[str] = mapped_column(String(3))
    period_year: Mapped[int] = mapped_column(Integer)
    import_value_usd: Mapped[float] = mapped_column(Float)
    import_value_prev_year: Mapped[float | None] = mapped_column(Float)
    import_value_3y_ago: Mapped[float | None] = mapped_column(Float)
    yoy_growth: Mapped[float | None] = mapped_column(Float)
    cagr_3y: Mapped[float | None] = mapped_column(Float)
    china_import_value_usd: Mapped[float | None] = mapped_column(Float)
    china_import_share: Mapped[float | None] = mapped_column(Float)
    unit_value_usd: Mapped[float | None] = mapped_column(Float)
    market_volatility: Mapped[float | None] = mapped_column(Float)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MarketOpportunity(Base):
    __tablename__ = "market_opportunities"
    __table_args__ = (
        UniqueConstraint(
            "hs_code", "origin_iso3", "destination_iso3", "period_year", "score_version"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    product_scope_type: Mapped[str] = mapped_column(String(20), default="HS")
    product_scope_id: Mapped[str | None] = mapped_column(String(120))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("product_entities.id"))
    hs_code: Mapped[str] = mapped_column(String(10), index=True)
    origin_iso3: Mapped[str] = mapped_column(String(3))
    destination_iso3: Mapped[str] = mapped_column(String(3), index=True)
    channel: Mapped[str | None] = mapped_column(String(80))
    period_year: Mapped[int] = mapped_column(Integer)
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    market_attractiveness_score: Mapped[float] = mapped_column(Float)
    data_coverage_score: Mapped[float] = mapped_column(Float)
    size_score: Mapped[float | None] = mapped_column(Float)
    growth_score: Mapped[float | None] = mapped_column(Float)
    momentum_score: Mapped[float | None] = mapped_column(Float)
    stability_score: Mapped[float | None] = mapped_column(Float)
    structural_demand_score: Mapped[float | None] = mapped_column(Float)
    digital_demand_score: Mapped[float | None] = mapped_column(Float)
    marketplace_demand_score: Mapped[float | None] = mapped_column(Float)
    explicit_demand_score: Mapped[float | None] = mapped_column(Float)
    market_access_score: Mapped[float | None] = mapped_column(Float)
    country_capacity_score: Mapped[float | None] = mapped_column(Float)
    supply_fit_score: Mapped[float | None] = mapped_column(Float)
    economics_score: Mapped[float | None] = mapped_column(Float)
    competition_score: Mapped[float | None] = mapped_column(Float)
    risk_score: Mapped[float | None] = mapped_column(Float)
    distribution_opportunity_score: Mapped[float | None] = mapped_column(Float)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    rank_global: Mapped[int | None] = mapped_column(Integer)
    score_version: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(20), default="CURRENT")
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    metric_key: Mapped[str] = mapped_column(String(80))
    value_numeric: Mapped[float | None] = mapped_column(Float)
    value_text: Mapped[str | None] = mapped_column(Text)
    value_json: Mapped[dict | list | None] = mapped_column(JSON)
    unit: Mapped[str | None] = mapped_column(String(40))
    currency: Mapped[str | None] = mapped_column(String(3))
    source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(40))
    source_identifier: Mapped[str] = mapped_column(String(300))
    source_url: Mapped[str | None] = mapped_column(Text)
    source_reliability: Mapped[str] = mapped_column(String(20), default=SourceReliability.A.value)
    observed_type: Mapped[str] = mapped_column(String(20), default=ObservedType.REPORTED.value)
    period: Mapped[str] = mapped_column(String(40))
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    raw_value: Mapped[float | str | dict | None] = mapped_column(JSON)
    display_value: Mapped[str] = mapped_column(String(160))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    raw_snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("source_snapshots.id"))
    confidence: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    hs_code: Mapped[str] = mapped_column(String(10), index=True)
    origin_iso3: Mapped[str] = mapped_column(String(3))
    requested_year: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default=AnalysisStatus.PENDING.value)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    countries_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    countries_succeeded: Mapped[int] = mapped_column(Integer, default=0)
    countries_failed: Mapped[int] = mapped_column(Integer, default=0)
    score_version: Mapped[str] = mapped_column(String(60), default="market_attractiveness_v1")
    error_message: Mapped[str | None] = mapped_column(Text)


class SupplyProductLink(Base):
    __tablename__ = "supply_product_links"
    id: Mapped[int] = mapped_column(primary_key=True)
    external_system: Mapped[str] = mapped_column(String(80))
    external_product_id: Mapped[str] = mapped_column(String(120))
    hs_code: Mapped[str] = mapped_column(String(10), index=True)
    mapping_confidence: Mapped[float] = mapped_column(Float)
    mapping_source: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    confirmed_by: Mapped[str | None] = mapped_column(String(120))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class DataSource(Base):
    __tablename__ = "data_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(30), index=True)
    provider_type: Mapped[str] = mapped_column(String(80))
    base_url: Mapped[str | None] = mapped_column(Text)
    reliability: Mapped[str] = mapped_column(String(20))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    update_frequency: Mapped[str | None] = mapped_column(String(80))
    freshness_ttl_hours: Mapped[int | None] = mapped_column(Integer)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="NOT_CONNECTED")
    terms_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class HsClassification(Base):
    __tablename__ = "hs_classifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class HsCorrespondence(Base):
    __tablename__ = "hs_correspondence"
    __table_args__ = (
        UniqueConstraint(
            "source_classification", "source_code", "target_classification", "target_code"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    source_classification: Mapped[str] = mapped_column(String(20))
    source_code: Mapped[str] = mapped_column(String(10), index=True)
    target_classification: Mapped[str] = mapped_column(String(20))
    target_code: Mapped[str] = mapped_column(String(10), index=True)
    mapping_type: Mapped[str] = mapped_column(String(30))
    confidence: Mapped[float | None] = mapped_column(Float)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.id"))


class ProductEntity(Base):
    __tablename__ = "product_entities"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(300), index=True)
    entity_type: Mapped[str] = mapped_column(String(30), default="PRODUCT")
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class ProductIdentifier(Base):
    __tablename__ = "product_identifiers"
    __table_args__ = (UniqueConstraint("identifier_type", "identifier_value", "source_system"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product_entities.id"), index=True)
    identifier_type: Mapped[str] = mapped_column(String(30))
    identifier_value: Mapped[str] = mapped_column(String(180), index=True)
    source_system: Mapped[str] = mapped_column(String(80), default="MARKET")
    confidence: Mapped[float | None] = mapped_column(Float)


class ProductHsMapping(Base):
    __tablename__ = "product_hs_mappings"
    __table_args__ = (UniqueConstraint("product_id", "classification", "hs_code"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product_entities.id"), index=True)
    classification: Mapped[str] = mapped_column(String(20))
    hs_code: Mapped[str] = mapped_column(String(10), index=True)
    confidence: Mapped[float | None] = mapped_column(Float)
    mapping_source: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    confirmed_by: Mapped[str | None] = mapped_column(String(120))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProductRelationship(Base):
    __tablename__ = "product_relationships"
    __table_args__ = (
        UniqueConstraint("source_product_id", "target_product_id", "relationship_type"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    source_product_id: Mapped[int] = mapped_column(ForeignKey("product_entities.id"), index=True)
    target_product_id: Mapped[int] = mapped_column(ForeignKey("product_entities.id"), index=True)
    relationship_type: Mapped[str] = mapped_column(String(30))
    confidence: Mapped[float | None] = mapped_column(Float)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")


class DemandSignal(Base):
    __tablename__ = "demand_signals"
    __table_args__ = (
        UniqueConstraint(
            "signal_layer",
            "hs_code",
            "country_iso3",
            "channel",
            "metric_key",
            "period_start",
            "source_id",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    signal_layer: Mapped[str] = mapped_column(String(30), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("product_entities.id"), index=True)
    hs_code: Mapped[str | None] = mapped_column(String(10), index=True)
    country_iso3: Mapped[str] = mapped_column(String(3), index=True)
    channel: Mapped[str | None] = mapped_column(String(80))
    metric_key: Mapped[str] = mapped_column(String(100))
    value_numeric: Mapped[float | None] = mapped_column(Float)
    value_text: Mapped[str | None] = mapped_column(Text)
    normalized_value: Mapped[float | None] = mapped_column(Float)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"), index=True)
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.id"))
    observed_type: Mapped[str] = mapped_column(String(20))
    source_reliability: Mapped[str] = mapped_column(String(20))
    freshness_status: Mapped[str] = mapped_column(String(20), default=FreshnessStatus.UNKNOWN.value)
    confidence: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MarketplaceSignal(Base):
    __tablename__ = "marketplace_signals"
    __table_args__ = (
        UniqueConstraint("marketplace", "country_iso3", "product_ref", "observed_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    marketplace: Mapped[str] = mapped_column(String(80), index=True)
    country_iso3: Mapped[str] = mapped_column(String(3), index=True)
    keyword: Mapped[str | None] = mapped_column(String(300))
    product_ref: Mapped[str | None] = mapped_column(String(180))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    price: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String(3))
    rating: Mapped[float | None] = mapped_column(Float)
    review_count: Mapped[int | None] = mapped_column(Integer)
    review_growth: Mapped[float | None] = mapped_column(Float)
    rank: Mapped[int | None] = mapped_column(Integer)
    rank_change: Mapped[int | None] = mapped_column(Integer)
    seller_count: Mapped[int | None] = mapped_column(Integer)
    promotion_flag: Mapped[bool | None] = mapped_column(Boolean)
    stock_status: Mapped[str | None] = mapped_column(String(40))
    estimated_sales: Mapped[float | None] = mapped_column(Float)
    observed_type: Mapped[str] = mapped_column(String(20))
    source_reliability: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float | None] = mapped_column(Float)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"))


class ExplicitDemand(Base):
    __tablename__ = "explicit_demands"
    __table_args__ = (UniqueConstraint("source_type", "source_identifier"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    source_type: Mapped[str] = mapped_column(String(40), index=True)
    source_identifier: Mapped[str] = mapped_column(String(300))
    buyer_name: Mapped[str | None] = mapped_column(String(300))
    buyer_country_iso3: Mapped[str] = mapped_column(String(3), index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    hs_code: Mapped[str | None] = mapped_column(String(10), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("product_entities.id"))
    quantity: Mapped[float | None] = mapped_column(Float)
    quantity_unit: Mapped[str | None] = mapped_column(String(40))
    budget_min: Mapped[float | None] = mapped_column(Float)
    budget_max: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String(3))
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    requirements: Mapped[dict] = mapped_column(JSON, default=dict)
    source_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30))
    observed_type: Mapped[str] = mapped_column(String(20), default=ObservedType.OBSERVED.value)
    source_reliability: Mapped[str] = mapped_column(String(20))
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MarketAccessMetric(Base):
    __tablename__ = "market_access_metrics"
    __table_args__ = (
        UniqueConstraint("hs_code", "country_iso3", "origin_iso3", "period_year", "source_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    hs_code: Mapped[str] = mapped_column(String(10), index=True)
    country_iso3: Mapped[str] = mapped_column(String(3), index=True)
    origin_iso3: Mapped[str] = mapped_column(String(3), default="CHN")
    period_year: Mapped[int] = mapped_column(Integer)
    mfn_tariff: Mapped[float | None] = mapped_column(Float)
    preferential_tariff: Mapped[float | None] = mapped_column(Float)
    china_applicable_tariff: Mapped[float | None] = mapped_column(Float)
    bound_tariff: Mapped[float | None] = mapped_column(Float)
    duty_free_flag: Mapped[bool | None] = mapped_column(Boolean)
    ntm_count: Mapped[int | None] = mapped_column(Integer)
    ntm_categories: Mapped[list | None] = mapped_column(JSON)
    market_access_score: Mapped[float | None] = mapped_column(Float)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"))
    observed_type: Mapped[str] = mapped_column(String(20), default=ObservedType.REPORTED.value)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CountryMetric(Base):
    __tablename__ = "country_metrics"
    __table_args__ = (UniqueConstraint("country_iso3", "metric_key", "period_year", "source_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    country_iso3: Mapped[str] = mapped_column(String(3), index=True)
    metric_key: Mapped[str] = mapped_column(String(100), index=True)
    value_numeric: Mapped[float | None] = mapped_column(Float)
    value_text: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(String(40))
    period_year: Mapped[int] = mapped_column(Integer)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"))
    observed_type: Mapped[str] = mapped_column(String(20), default=ObservedType.REPORTED.value)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SupplyFit(Base):
    __tablename__ = "supply_fit"
    id: Mapped[int] = mapped_column(primary_key=True)
    hs_code: Mapped[str | None] = mapped_column(String(10), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("product_entities.id"))
    country_iso3: Mapped[str | None] = mapped_column(String(3), index=True)
    channel: Mapped[str | None] = mapped_column(String(80))
    supplier_count: Mapped[int | None] = mapped_column(Integer)
    product_count: Mapped[int | None] = mapped_column(Integer)
    active_offer_count: Mapped[int | None] = mapped_column(Integer)
    min_price: Mapped[float | None] = mapped_column(Float)
    median_price: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String(3))
    moq_min: Mapped[float | None] = mapped_column(Float)
    moq_median: Mapped[float | None] = mapped_column(Float)
    stock_total: Mapped[float | None] = mapped_column(Float)
    lead_time_min: Mapped[float | None] = mapped_column(Float)
    lead_time_median: Mapped[float | None] = mapped_column(Float)
    certified_supplier_count: Mapped[int | None] = mapped_column(Integer)
    dropship_supplier_count: Mapped[int | None] = mapped_column(Integer)
    quality_score: Mapped[float | None] = mapped_column(Float)
    supply_fit_score: Mapped[float | None] = mapped_column(Float)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.id"))
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DistributionEconomics(Base):
    __tablename__ = "distribution_economics"
    id: Mapped[int] = mapped_column(primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("market_opportunities.id"), index=True)
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    landed_cost: Mapped[float | None] = mapped_column(Float)
    channel_cost: Mapped[float | None] = mapped_column(Float)
    total_variable_cost: Mapped[float | None] = mapped_column(Float)
    target_sale_price: Mapped[float | None] = mapped_column(Float)
    gross_profit: Mapped[float | None] = mapped_column(Float)
    contribution_profit: Mapped[float | None] = mapped_column(Float)
    gross_margin: Mapped[float | None] = mapped_column(Float)
    contribution_margin: Mapped[float | None] = mapped_column(Float)
    break_even_price: Mapped[float | None] = mapped_column(Float)
    input_source: Mapped[dict] = mapped_column(JSON, default=dict)
    calculation_version: Mapped[str] = mapped_column(String(60))
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class OpportunityRisk(Base):
    __tablename__ = "opportunity_risks"
    __table_args__ = (UniqueConstraint("opportunity_id", "risk_type"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("market_opportunities.id"), index=True)
    risk_type: Mapped[str] = mapped_column(String(50))
    score: Mapped[float | None] = mapped_column(Float)
    reason: Mapped[str | None] = mapped_column(Text)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="UNKNOWN")
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Watchlist(Base):
    __tablename__ = "watchlists"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("product_entities.id"))
    hs_code: Mapped[str | None] = mapped_column(String(10), index=True)
    country_iso3: Mapped[str | None] = mapped_column(String(3), index=True)
    channel: Mapped[str | None] = mapped_column(String(80))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class OpportunityEvent(Base):
    __tablename__ = "opportunity_events"
    __table_args__ = (UniqueConstraint("entity_type", "entity_id", "event_type", "detected_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    severity: Mapped[str] = mapped_column(String(20))
    before_value: Mapped[dict | float | str | None] = mapped_column(JSON)
    after_value: Mapped[dict | float | str | None] = mapped_column(JSON)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class OpportunityOutcome(Base):
    __tablename__ = "opportunity_outcomes"
    __table_args__ = (UniqueConstraint("opportunity_id", "action", "period", "source"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("market_opportunities.id"), index=True)
    action: Mapped[str] = mapped_column(String(40))
    actual_gmv: Mapped[float | None] = mapped_column(Float)
    actual_orders: Mapped[int | None] = mapped_column(Integer)
    actual_profit: Mapped[float | None] = mapped_column(Float)
    actual_margin: Mapped[float | None] = mapped_column(Float)
    conversion: Mapped[float | None] = mapped_column(Float)
    return_rate: Mapped[float | None] = mapped_column(Float)
    period: Mapped[str] = mapped_column(String(30))
    source: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DecisionRecommendation(Base):
    __tablename__ = "decision_recommendations"
    id: Mapped[int] = mapped_column(primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("market_opportunities.id"), index=True)
    recommendation: Mapped[str] = mapped_column(String(40))
    reason: Mapped[str] = mapped_column(Text)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[float | None] = mapped_column(Float)
    human_status: Mapped[str] = mapped_column(String(30), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DistributionPlan(Base):
    __tablename__ = "distribution_plans"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("market_opportunities.id"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("product_entities.id"))
    destination_iso3: Mapped[str] = mapped_column(String(3))
    channel: Mapped[str | None] = mapped_column(String(80))
    supplier_offer_ref: Mapped[str | None] = mapped_column(String(180))
    target_price: Mapped[float | None] = mapped_column(Float)
    expected_cost: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String(3))
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT")
    erp_reference: Mapped[str | None] = mapped_column(String(180))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MetricDefinition(Base):
    __tablename__ = "metric_definitions"
    id: Mapped[int] = mapped_column(primary_key=True)
    metric_key: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(String(40))
    higher_is_better: Mapped[bool | None] = mapped_column(Boolean)
    source_layer: Mapped[str] = mapped_column(String(30))
    normalization: Mapped[dict | None] = mapped_column(JSON)


class DataJob(Base):
    __tablename__ = "data_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_type: Mapped[str] = mapped_column(String(30), index=True)
    provider_code: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
