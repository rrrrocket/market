from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProductOut(ORMModel):
    hs_code: str
    name_en: str
    name_zh: str | None
    level: int


class CountryOut(ORMModel):
    iso2: str
    iso3: str
    name_en: str
    name_zh: str | None
    region: str | None


class AnalysisCreate(BaseModel):
    hs_code: str = Field(pattern=r"^\d{4,10}$")
    origin_iso3: str = Field(default="CHN", min_length=3, max_length=3)


class AnalysisOut(ORMModel):
    id: str
    analysis_id: str | None = None
    hs_code: str
    origin_iso3: str
    requested_year: int
    status: str
    countries_analyzed: int
    countries_succeeded: int
    countries_failed: int
    score_version: str
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None

    @model_validator(mode="after")
    def expose_analysis_id(self):
        self.analysis_id = self.analysis_id or self.id
        return self


class OpportunityListItem(BaseModel):
    id: int
    rank: int | None
    hs_code: str
    destination_iso3: str
    country_name: str
    region: str | None
    period_year: int
    score: float
    coverage: float
    import_value_usd: float
    cagr_3y: float | None
    yoy_growth: float | None
    china_share: float | None
    size_score: float | None
    growth_score: float | None
    momentum_score: float | None
    stability_score: float | None


class HistoryItem(BaseModel):
    year: int
    import_value_usd: float
    china_value_usd: float | None
    china_share: float | None


class SupplierItem(BaseModel):
    supplier_iso3: str
    supplier_name: str
    trade_value_usd: float
    share: float
    rank: int


class WatchlistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    product_id: int | None = None
    hs_code: str | None = Field(default=None, pattern=r"^\d{2,10}$")
    country_iso3: str | None = Field(default=None, min_length=3, max_length=3)
    channel: str | None = Field(default=None, max_length=80)


class DatasetImportRequest(BaseModel):
    dataset_type: str
    provider_code: str
    format: str = Field(pattern=r"^(CSV|JSON|PARQUET)$")
    records: list[dict]
    source_revision: str | None = None


class DatasetFileImportRequest(BaseModel):
    dataset_type: str
    provider_code: str
    format: str = Field(pattern=r"^(CSV|JSON|PARQUET)$")
    content_base64: str
    source_revision: str | None = None


class DataSourceUpdate(BaseModel):
    reliability: str | None = Field(default=None, pattern=r"^(A_PLUS|A|A_MINUS|B_PLUS|B|C|D)$")
    enabled: bool | None = None
    freshness_ttl_hours: int | None = Field(default=None, ge=1)
    terms_notes: str | None = None


class DistributionPlanCreate(BaseModel):
    opportunity_id: int
    product_id: int | None = None
    channel: str | None = Field(default=None, max_length=80)
    supplier_offer_ref: str | None = Field(default=None, max_length=180)
    target_price: float | None = Field(default=None, ge=0)
    expected_cost: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    evidence_ids: list[int] = Field(default_factory=list)
