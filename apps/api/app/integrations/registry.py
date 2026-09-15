from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.integrations.base import Provider, ProviderMetadata
from app.integrations.demand import (
    NullExplicitDemandProvider,
    NullSearchDemandProvider,
    TedExplicitDemandProvider,
)
from app.integrations.macro import WorldBankProvider
from app.integrations.marketplace import (
    EbayMarketplaceProvider,
    HttpMarketplaceProvider,
    NullMarketplaceProvider,
)
from app.integrations.supplier import HttpSupplierNetworkClient, NullSupplierNetworkClient
from app.integrations.tariff import WitsTariffProvider, WtoTariffProvider
from app.integrations.trade import ComtradeTradeDataProvider, FixtureTradeDataProvider


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, Provider] = {}

    def register(self, provider: Provider) -> None:
        code = provider.metadata.code
        if code in self._providers:
            raise ValueError(f"Provider already registered: {code}")
        self._providers[code] = provider

    def get(self, code: str) -> Provider:
        if code not in self._providers:
            raise KeyError(f"Unknown provider: {code}")
        return self._providers[code]

    def describe(self) -> list[dict]:
        return [provider.metadata.model_dump() for provider in self._providers.values()]

    @property
    def metadata(self) -> tuple[ProviderMetadata, ...]:
        return tuple(provider.metadata for provider in self._providers.values())


def build_provider_registry(settings: Settings) -> ProviderRegistry:
    registry = ProviderRegistry()
    fixture = next(
        (
            root / "data/fixtures/comtrade/hs_902620_test.json"
            for root in Path(__file__).resolve().parents
            if (root / "data/fixtures/comtrade/hs_902620_test.json").exists()
        ),
        Path("/data/fixtures/comtrade/hs_902620_test.json"),
    )
    if settings.trade_data_provider.lower() in {"comtrade", "un_comtrade"}:
        registry.register(
            ComtradeTradeDataProvider(
                settings.comtrade_api_key,
                base_url=settings.comtrade_api_base_url,
                final_base_url=settings.comtrade_final_api_base_url,
                max_concurrency=settings.comtrade_max_concurrency,
                retry_attempts=settings.provider_retry_attempts,
                retry_delay_seconds=settings.provider_retry_delay_seconds,
            )
        )
    else:
        registry.register(FixtureTradeDataProvider(fixture))
    registry.register(
        WorldBankProvider(
            enabled=settings.enable_world_bank,
            base_url=settings.world_bank_api_base_url,
        )
    )
    registry.register(
        WitsTariffProvider(
            enabled=settings.enable_wits,
            base_url=settings.wits_api_base_url,
        )
    )
    registry.register(WtoTariffProvider(settings.wto_api_key, enabled=settings.enable_wto))
    registry.register(NullSearchDemandProvider())
    if settings.ebay_client_id and settings.ebay_client_secret:
        registry.register(
            EbayMarketplaceProvider(
                settings.ebay_client_id,
                settings.ebay_client_secret,
                base_url=settings.ebay_api_base_url,
                oauth_url=settings.ebay_oauth_url,
                timeout_seconds=settings.marketplace_api_timeout_seconds,
            )
        )
    elif (
        settings.marketplace_provider_code
        and settings.marketplace_api_base_url
        and settings.marketplace_api_key
    ):
        registry.register(
            HttpMarketplaceProvider(
                settings.marketplace_provider_code,
                settings.marketplace_api_base_url,
                settings.marketplace_api_key,
                timeout_seconds=settings.marketplace_api_timeout_seconds,
            )
        )
    else:
        registry.register(NullMarketplaceProvider())
    if settings.enable_ted:
        registry.register(
            TedExplicitDemandProvider(enabled=True, base_url=settings.ted_api_base_url)
        )
    else:
        registry.register(NullExplicitDemandProvider())
    if (
        (settings.enable_supplier or settings.supplier_integration_enabled)
        and settings.supplier_api_base_url
        and settings.supplier_api_key
    ):
        registry.register(
            HttpSupplierNetworkClient(
                settings.supplier_api_base_url,
                settings.supplier_api_key,
                timeout_seconds=settings.supplier_api_timeout_seconds,
            )
        )
    else:
        registry.register(NullSupplierNetworkClient())
    return registry
