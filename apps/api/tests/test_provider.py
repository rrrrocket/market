import httpx
import pytest

from app.core.config import get_settings
from app.integrations.country_codes import (
    comtrade_area_to_iso3,
    iso3_to_comtrade_reporter,
    iso3_to_m49,
    m49_to_iso3,
)
from app.integrations.demand import TedExplicitDemandProvider
from app.integrations.macro import WorldBankProvider
from app.integrations.marketplace import EbayMarketplaceProvider
from app.integrations.registry import build_provider_registry
from app.integrations.tariff import FixtureTariffProvider, WitsTariffProvider
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
    snapshot = provider.snapshot_payload(records)
    assert snapshot[0]["period_start"] == "2025-01-01"
    assert snapshot[0]["period_end"] == "2025-12-31"
    await client.aclose()


@pytest.mark.asyncio
async def test_comtrade_converts_iso3_query_codes_and_numeric_response():
    def handler(request: httpx.Request):
        assert request.url.params["reporterCode"] == "792"
        assert request.url.params["partnerCode"] == "0,156"
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "cmdCode": "902620",
                        "reporterCode": 792,
                        "partnerCode": 0,
                        "primaryValue": 1000,
                    }
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = ComtradeTradeDataProvider(client=client)
    records = await provider.get_imports("902620", 2025, "TUR", "WLD,CHN")
    assert records[0].reporter_iso3 == "TUR"
    assert records[0].partner_iso3 == "WLD"
    await client.aclose()


def test_country_code_resolver_is_bidirectional():
    assert iso3_to_m49("CHN") == "156"
    assert m49_to_iso3("156") == "CHN"
    assert iso3_to_m49("WLD") == "0"


def test_comtrade_reporter_codes_handle_non_m49_identifiers():
    assert iso3_to_comtrade_reporter("USA") == "842"
    assert iso3_to_comtrade_reporter("IND") == "699"
    assert iso3_to_comtrade_reporter("DEU") == "276"
    assert comtrade_area_to_iso3(842) == "USA"
    assert comtrade_area_to_iso3(699) == "IND"


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
async def test_comtrade_retries_transient_connection_errors():
    attempts = 0

    def handler(request: httpx.Request):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectError("temporary", request=request)
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "cmdCode": "902620",
                        "reporterISO": "USA",
                        "partnerISO": "WLD",
                        "primaryValue": 1000,
                    }
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = ComtradeTradeDataProvider(
        client=client, retry_attempts=2, retry_delay_seconds=0
    )
    rows = await provider.get_imports("902620", 2024, "USA", "WLD")
    assert attempts == 2
    assert rows[0].trade_value_usd == 1000
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


@pytest.mark.asyncio
async def test_wits_uses_numeric_sdmx_key_and_parses_xml():
    xml = b"""<?xml version="1.0"?>
    <message:GenericData xmlns:message="urn:sdmx:org.sdmx.infomodel.message:2.1"
      xmlns:generic="urn:sdmx:org.sdmx.infomodel.data.generic:2.1">
      <message:DataSet><generic:Series>
        <generic:SeriesKey>
          <generic:Value id="TARIFFTYPE" value="MFN"/>
          <generic:Value id="NOMENCODE" value="H6"/>
        </generic:SeriesKey>
        <generic:Obs><generic:ObsDimension value="2022"/><generic:ObsValue value="4.2"/></generic:Obs>
      </generic:Series></message:DataSet>
    </message:GenericData>"""

    def handler(request: httpx.Request):
        assert "A.792." in request.url.path
        if ".000." in request.url.path:
            return httpx.Response(200, content=xml)
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = WitsTariffProvider(client=client, enabled=True)
    rows = await provider.get_tariff("902620", "TUR", "CHN", 2022)
    assert rows[0].mfn_tariff == 4.2
    assert rows[0].preferential_tariff is None
    await client.aclose()


def test_provider_registry_exposes_disabled_integrations():
    registry = build_provider_registry(get_settings())
    providers = {item["code"]: item for item in registry.describe()}
    assert providers["GOOGLE_TRENDS"]["health"] == "LIMITED_ACCESS"
    assert providers["SUPPLIER_NETWORK"]["enabled"] is False


@pytest.mark.asyncio
async def test_ted_search_normalizes_observed_tender():
    def handler(request: httpx.Request):
        assert request.url.path == "/v3/notices/search"
        return httpx.Response(
            200,
            json={
                "notices": [
                    {
                        "publication-number": "123456-2026",
                        "notice-title": {"eng": "Pressure measurement instruments"},
                        "buyer-name": {"eng": ["Example authority"]},
                        "buyer-country": ["DEU"],
                        "publication-date": "2026-09-01+02:00",
                        "links": {
                            "htmlDirect": {
                                "ENG": "https://ted.europa.eu/en/notice/123456-2026/html"
                            }
                        },
                    }
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = TedExplicitDemandProvider(client=client)
    rows = await provider.search_demands(
        hs_code="902620", country_iso3="DEU", keyword="pressure instrument"
    )
    assert rows[0]["source_identifier"] == "123456-2026"
    assert rows[0]["buyer_country_iso3"] == "DEU"
    assert rows[0]["observed_type"] == "OBSERVED"
    await client.aclose()


@pytest.mark.asyncio
async def test_ebay_search_uses_oauth_and_keeps_unreported_metrics_empty():
    def handler(request: httpx.Request):
        if request.url.path == "/identity/v1/oauth2/token":
            return httpx.Response(200, json={"access_token": "token", "expires_in": 7200})
        assert request.headers["x-ebay-c-marketplace-id"] == "EBAY_DE"
        return httpx.Response(
            200,
            json={
                "itemSummaries": [
                    {
                        "itemId": "v1|123|0",
                        "price": {"value": "24.50", "currency": "EUR"},
                        "seller": {"username": "seller-a"},
                        "buyingOptions": ["FIXED_PRICE"],
                    }
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = EbayMarketplaceProvider("client", "secret", client=client)
    rows = await provider.get_keyword_metrics("EBAY_DE", "DEU", "pressure sensor")
    assert rows[0]["price"] == "24.50"
    assert rows[0]["currency"] == "EUR"
    assert "rating" not in rows[0]
    assert "estimated_sales" not in rows[0]
    await client.aclose()
