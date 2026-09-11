from datetime import UTC, datetime
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    public_web_url: str = "https://market.matrix-one.tech"
    database_url: str = "sqlite:///./market.db"
    trade_data_provider: str = "fixture"
    comtrade_api_key: str = ""
    comtrade_cache_ttl_days: int = 30
    trade_annual_cache_ttl_hours: int = 8760
    trade_monthly_cache_ttl_hours: int = 1440
    tariff_cache_ttl_hours: int = 8760
    macro_cache_ttl_hours: int = 8760
    search_cache_ttl_hours: int = 168
    marketplace_cache_ttl_hours: int = 24
    tender_cache_ttl_hours: int = 24
    supplier_cache_ttl_hours: int = 24
    default_origin_iso3: str = "CHN"
    min_market_import_value_usd: float = 100_000
    latest_complete_trade_year: int | None = None
    supplier_api_base_url: str = ""
    supplier_api_key: str = ""
    supplier_integration_enabled: bool = False
    enable_world_bank: bool = True
    enable_wits: bool = False
    enable_wto: bool = False
    enable_google_trends: bool = False
    enable_ozon: bool = False
    enable_wildberries: bool = False
    enable_amazon: bool = False
    enable_tender: bool = False
    enable_supplier: bool = False
    wto_api_key: str = ""
    admin_email: str = "admin@matrix-one.tech"
    admin_password: str = "change-me"

    @property
    def latest_complete_year(self) -> int:
        # Trade datasets typically lag the calendar by at least one full year.
        return self.latest_complete_trade_year or datetime.now(UTC).year - 1

    @property
    def cache_ttl_hours(self) -> dict[str, int]:
        return {
            "TRADE_ANNUAL": self.trade_annual_cache_ttl_hours,
            "TRADE_MONTHLY": self.trade_monthly_cache_ttl_hours,
            "TARIFF": self.tariff_cache_ttl_hours,
            "MACRO": self.macro_cache_ttl_hours,
            "SEARCH": self.search_cache_ttl_hours,
            "MARKETPLACE": self.marketplace_cache_ttl_hours,
            "TENDER": self.tender_cache_ttl_hours,
            "SUPPLIER": self.supplier_cache_ttl_hours,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
