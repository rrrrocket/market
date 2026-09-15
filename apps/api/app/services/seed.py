import json
from pathlib import Path

import pycountry
from babel import Locale
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Country,
    DataSource,
    HsClassification,
    HsProduct,
    MetricDefinition,
    ProductEntity,
    ProductHsMapping,
)

COUNTRIES = [
    ("US", "USA", "840", "United States", "美国", "Americas", "Northern America"),
    ("DE", "DEU", "276", "Germany", "德国", "Europe", "Western Europe"),
    ("TR", "TUR", "792", "Türkiye", "土耳其", "Asia", "Western Asia"),
    ("IN", "IND", "356", "India", "印度", "Asia", "Southern Asia"),
    ("RU", "RUS", "643", "Russia", "俄罗斯", "Europe", "Eastern Europe"),
    ("BR", "BRA", "076", "Brazil", "巴西", "Americas", "South America"),
    ("MX", "MEX", "484", "Mexico", "墨西哥", "Americas", "Central America"),
    ("JP", "JPN", "392", "Japan", "日本", "Asia", "Eastern Asia"),
    ("GB", "GBR", "826", "United Kingdom", "英国", "Europe", "Northern Europe"),
    ("AE", "ARE", "784", "United Arab Emirates", "阿联酋", "Asia", "Western Asia"),
    ("ZA", "ZAF", "710", "South Africa", "南非", "Africa", "Southern Africa"),
    ("PL", "POL", "616", "Poland", "波兰", "Europe", "Eastern Europe"),
    ("CN", "CHN", "156", "China", "中国", "Asia", "Eastern Asia"),
]

ZH_TERRITORIES = Locale.parse("zh_CN").territories

DATA_SOURCES = [
    (
        "COMTRADE_FIXTURE",
        "UN Comtrade fixture",
        "TRADE",
        "FixtureTradeDataProvider",
        None,
        "A",
        True,
        "STATIC",
        None,
        "READY",
        "Deterministic TEST DATA; never present as current observed production data.",
    ),
    (
        "UN_COMTRADE",
        "UN Comtrade",
        "TRADE",
        "ComtradeTradeDataProvider",
        "https://comtradeapi.un.org",
        "A",
        False,
        "ANNUAL_MONTHLY",
        8760,
        "AVAILABLE",
        "Live use requires explicit configuration and respects official API limits.",
    ),
    (
        "WITS_TRAINS",
        "WITS / UNCTAD TRAINS",
        "TARIFF",
        "WitsTariffProvider",
        "https://wits.worldbank.org",
        "A",
        True,
        "ANNUAL",
        8760,
        "AVAILABLE",
        "Tariff values are reported at supported HS revisions; correspondence is required.",
    ),
    (
        "WTO",
        "World Trade Organization",
        "TARIFF",
        "WtoTariffProvider",
        "https://api.wto.org",
        "A",
        False,
        "ANNUAL",
        8760,
        "AUTH_REQUIRED",
        "WTO API subscription key required.",
    ),
    (
        "WORLD_BANK",
        "World Bank Indicators",
        "MACRO",
        "WorldBankProvider",
        "https://api.worldbank.org",
        "A",
        True,
        "ANNUAL",
        8760,
        "AVAILABLE",
        None,
    ),
    (
        "GOOGLE_TRENDS",
        "Google Trends API (alpha)",
        "SEARCH",
        "GoogleTrendsProvider",
        None,
        "B_PLUS",
        False,
        "WEEKLY",
        168,
        "LIMITED_ACCESS",
        "Normalized interest only; never absolute search volume.",
    ),
    (
        "MARKETPLACES",
        "eBay Browse API",
        "MARKETPLACE",
        "EbayMarketplaceProvider",
        "https://api.ebay.com/buy/browse/v1",
        "A_MINUS",
        False,
        "DAILY",
        24,
        "AUTH_REQUIRED",
        "Official eBay application access token required.",
    ),
    (
        "EXPLICIT_DEMAND",
        "TED EU Tenders",
        "TENDER",
        "TedExplicitDemandProvider",
        "https://api.ted.europa.eu/v3/notices/search",
        "A_MINUS",
        True,
        "DAILY",
        24,
        "AVAILABLE",
        "Published procurement notice search; no authentication required.",
    ),
    (
        "SUPPLIER_NETWORK",
        "Matrix One Supplier Network",
        "SUPPLY",
        "NullSupplierNetworkClient",
        None,
        "A",
        False,
        "DAILY",
        24,
        "AUTH_REQUIRED",
        "API-only integration; Market does not access the Supplier database.",
    ),
]

METRICS = [
    ("IMPORT_VALUE", "Importer-reported imports", "USD", True, "STRUCTURAL"),
    ("CAGR_3Y", "Three-year import CAGR", "RATIO", True, "STRUCTURAL"),
    ("YOY_GROWTH", "Latest import growth", "RATIO", True, "STRUCTURAL"),
    ("CHINA_SHARE", "China share of destination imports", "RATIO", None, "STRUCTURAL"),
    ("MFN_TARIFF", "MFN tariff", "PERCENT", False, "ACCESS"),
    ("GDP_USD", "Gross domestic product", "USD", True, "MACRO"),
    ("GDP_PER_CAPITA", "GDP per capita", "USD", True, "MACRO"),
    ("POPULATION", "Population", "PERSON", True, "MACRO"),
]


def seed_reference_data(db: Session) -> None:
    if (db.scalar(select(func.count()).select_from(HsProduct)) or 0) < 6_000:
        relative = Path("data/seeds/hs2022.json")
        catalog_path = next(
            (
                root / relative
                for root in Path(__file__).resolve().parents
                if (root / relative).exists()
            ),
            Path("/") / relative,
        )
        catalog = json.loads(catalog_path.read_text())
        existing = {product.hs_code: product for product in db.scalars(select(HsProduct)).all()}
        for item in catalog["results"]:
            code = item["id"]
            if code == "TOTAL":
                continue
            name = item["text"].removeprefix(f"{code} - ")
            parent = item.get("parent")
            values = {
                "classification": "HS2022",
                "hs_code": code,
                "level": int(item["aggrlevel"]),
                "parent_code": parent if parent not in {"#", "TOTAL"} else None,
                "name_en": name,
                "description": name,
            }
            if code in existing:
                for key, value in values.items():
                    setattr(existing[code], key, value)
            else:
                db.add(HsProduct(**values))
    existing = set(db.scalars(select(Country.iso3)).all())
    db.add_all(
        [
            Country(iso2=a, iso3=b, numeric_code=c, name_en=d, name_zh=e, region=f, subregion=g)
            for a, b, c, d, e, f, g in COUNTRIES
            if b not in existing
        ]
    )
    existing.update(item[1] for item in COUNTRIES)
    db.add_all(
        [
            Country(
                iso2=country.alpha_2,
                iso3=country.alpha_3,
                numeric_code=country.numeric,
                name_en=country.name,
                name_zh=None,
                region=None,
                subregion=None,
            )
            for country in pycountry.countries
            if country.alpha_3 not in existing
        ]
    )
    db.flush()
    for country in db.scalars(select(Country)).all():
        if not country.name_zh:
            country.name_zh = ZH_TERRITORIES.get(country.iso2)
    existing_sources = {source.code for source in db.scalars(select(DataSource)).all()}
    db.add_all(
        [
            DataSource(
                code=code,
                name=name,
                category=category,
                provider_type=provider,
                base_url=url,
                reliability=reliability,
                enabled=enabled,
                update_frequency=frequency,
                freshness_ttl_hours=ttl,
                status=status,
                terms_notes=notes,
            )
            for code, name, category, provider, url, reliability, enabled, frequency, ttl, status, notes in DATA_SOURCES
            if code not in existing_sources
        ]
    )
    existing_classifications = set(db.scalars(select(HsClassification.code)).all())
    db.add_all(
        [
            HsClassification(
                code=code, name=f"Harmonized System {year}", is_active=code == "HS2022"
            )
            for code, year in (("HS2012", 2012), ("HS2017", 2017), ("HS2022", 2022))
            if code not in existing_classifications
        ]
    )
    existing_metrics = set(db.scalars(select(MetricDefinition.metric_key)).all())
    db.add_all(
        [
            MetricDefinition(
                metric_key=key, name=name, unit=unit, higher_is_better=higher, source_layer=layer
            )
            for key, name, unit, higher, layer in METRICS
            if key not in existing_metrics
        ]
    )
    pressure = db.scalar(
        select(ProductEntity).where(ProductEntity.name == "Pressure measurement instruments")
    )
    if pressure is None:
        pressure = ProductEntity(
            name="Pressure measurement instruments", entity_type="CATEGORY", status="ACTIVE"
        )
        db.add(pressure)
        db.flush()
    mapping = db.scalar(
        select(ProductHsMapping).where(
            ProductHsMapping.product_id == pressure.id,
            ProductHsMapping.classification == "HS2022",
            ProductHsMapping.hs_code == "902620",
        )
    )
    if mapping is None:
        db.add(
            ProductHsMapping(
                product_id=pressure.id,
                classification="HS2022",
                hs_code="902620",
                confidence=1.0,
                mapping_source="OFFICIAL_CATALOG",
                status="CONFIRMED",
                confirmed_by="SYSTEM",
            )
        )
    db.commit()
