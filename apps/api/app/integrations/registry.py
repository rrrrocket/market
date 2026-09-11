from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.integrations.base import Provider, ProviderMetadata
from app.integrations.demand import NullExplicitDemandProvider, NullSearchDemandProvider
from app.integrations.macro import FixtureMacroProvider, WorldBankProvider
from app.integrations.marketplace import NullMarketplaceProvider
from app.integrations.supplier import NullSupplierNetworkClient
from app.integrations.tariff import NullTariffProvider, WitsTariffProvider, WtoTariffProvider
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
        (root / "data/fixtures/comtrade/hs_902620_test.json" for root in Path(__file__).resolve().parents if (root / "data/fixtures/comtrade/hs_902620_test.json").exists()),
        Path("/data/fixtures/comtrade/hs_902620_test.json"),
    )
    registry.register(FixtureTradeDataProvider(fixture))
    if settings.trade_data_provider.lower() in {"comtrade", "un_comtrade"}:
        registry.register(ComtradeTradeDataProvider(settings.comtrade_api_key))
    registry.register(WorldBankProvider(enabled=settings.enable_world_bank))
    registry.register(FixtureMacroProvider())
    registry.register(WitsTariffProvider(enabled=settings.enable_wits))
    registry.register(WtoTariffProvider(settings.wto_api_key, enabled=settings.enable_wto))
    registry.register(NullTariffProvider())
    registry.register(NullSearchDemandProvider())
    registry.register(NullMarketplaceProvider())
    registry.register(NullExplicitDemandProvider())
    registry.register(NullSupplierNetworkClient())
    return registry
