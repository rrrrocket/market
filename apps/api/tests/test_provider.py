import httpx
import pytest

from app.core.config import get_settings
from app.integrations.macro import WorldBankProvider
from app.integrations.registry import build_provider_registry
from app.integrations.tariff import FixtureTariffProvider
from app.integrations.trade import ComtradeTradeDataProvider, FixtureTradeDataProvider
from app.services.analysis import fixture_path


@pytest.mark.asyncio
async def test_fixture_provider_returns_world_and_china_records():
    provider = FixtureTradeDataProvider(fixture_path())
    records = await provider.get_imports("902620", 2025, reporter="IND")
    assert {record.partner_iso3 for record in records} >= {"WLD", "CHN"}
    total = next(record for record in records if record.partner_iso3 == "WLD")
    china = next(record for record in records if record.partner_iso3 == "CHN")
    assert china.trade_value_usd / total.trade_value_usd == pytest.approx(0.22)


@pytest.mark.asyncio
async def test_comtrade_response_normalization():
    def handler(request: httpx.Request):
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "cmdCode": "902620",
                        "period": 2025,
                        "reporterISO": "IND",
                        "partnerISO": "CHN",
                        "primaryValue": 1000,
                        "netWgt": 25,
                    }
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = ComtradeTradeDataProvider(client=client)
    records = await provider.get_imports("902620", 2025, "IND", "CHN")
    assert records[0].trade_value_usd == 1000
    assert records[0].flow == "IMPORT"
    await client.aclose()


@pytest.mark.asyncio
async def test_comtrade_api_failure_is_explicit():
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(503, text="unavailable"))
    )
    provider = ComtradeTradeDataProvider(client=client)
    with pytest.raises(httpx.HTTPStatusError):
        await provider.get_imports("902620", 2025)
    await client.aclose()


@pytest.mark.asyncio
async def test_monthly_fixture_preserves_period_semantics():
    provider = FixtureTradeDataProvider(fixture_path())
    records = await provider.get_monthly_imports("902620", 2025, 3, reporter="TUR")
    assert records
    assert records[0].period_type == "MONTH"
    assert records[0].period_start.isoformat() == "2025-03-01"
    assert records[0].period_end.isoformat() == "2025-03-31"


@pytest.mark.asyncio
async def test_world_bank_normalization():
    def handler(request: httpx.Request):
        return httpx.Response(200, json=[{}, [{"date": "2024", "value": 123.5}]])

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = WorldBankProvider(client=client)
    rows = await provider.get_country_metrics("TUR", 2024)
    assert rows
    assert rows[0].country_iso3 == "TUR"
    assert rows[0].period_year == 2024
    await client.aclose()


@pytest.mark.asyncio
async def test_tariff_fixture_is_explicit_test_data():
    provider = FixtureTariffProvider()
    rows = await provider.get_tariff("902620", "TUR", "CHN", 2025)
    assert rows[0].mfn_tariff == 4.2
    assert provider.metadata.health == "TEST_DATA"


def test_provider_registry_exposes_disabled_integrations():
    registry = build_provider_registry(get_settings())
    providers = {item["code"]: item for item in registry.describe()}
    assert providers["GOOGLE_TRENDS"]["health"] == "NOT_CONNECTED"
    assert providers["SUPPLIER_NETWORK"]["enabled"] is False
