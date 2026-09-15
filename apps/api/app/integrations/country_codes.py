from __future__ import annotations

import pycountry

WORLD_CODES = {"0", "000", "WLD", "WORLD", "ALL"}

# UN Comtrade's current reporter-area identifiers are not always ISO 3166
# numeric/M49 identifiers. These values come from the official Reporters.json
# reference list. Partner codes remain M49-compatible for the countries used by
# the application (notably China = 156).
COMTRADE_REPORTER_CODE_OVERRIDES = {
    "FRA": "251",
    "IND": "699",
    "NOR": "579",
    "CHE": "757",
    "USA": "842",
}
COMTRADE_CODE_TO_ISO3 = {
    int(code): iso3 for iso3, code in COMTRADE_REPORTER_CODE_OVERRIDES.items()
}


def iso3_to_m49(value: str | None) -> str:
    if value is None or value.upper() in WORLD_CODES:
        return "0"
    cleaned = value.strip().upper()
    if cleaned.isdigit():
        return str(int(cleaned))
    country = pycountry.countries.get(alpha_3=cleaned)
    if country is None or not getattr(country, "numeric", None):
        raise ValueError(f"Unknown ISO3 country code: {value}")
    return str(int(country.numeric))


def m49_to_iso3(value: str | int | None) -> str:
    if value is None or str(value).strip() in WORLD_CODES:
        return "WLD"
    cleaned = str(value).strip().zfill(3)
    country = pycountry.countries.get(numeric=cleaned)
    if country is None:
        raise ValueError(f"Unknown UN M49 country code: {value}")
    return country.alpha_3


def iso3_to_comtrade_reporter(value: str | None) -> str:
    if value is None or value.upper() in WORLD_CODES:
        return "0"
    cleaned = value.strip().upper()
    if cleaned.isdigit():
        return str(int(cleaned))
    return COMTRADE_REPORTER_CODE_OVERRIDES.get(cleaned, iso3_to_m49(cleaned))


def comtrade_area_to_iso3(value: str | int | None) -> str:
    if value is None or str(value).strip() in WORLD_CODES:
        return "WLD"
    numeric = int(str(value).strip())
    overridden = COMTRADE_CODE_TO_ISO3.get(numeric)
    return overridden if overridden else m49_to_iso3(numeric)


def comma_separated_m49(value: str | None) -> str:
    if value is None:
        return "0"
    return ",".join(iso3_to_m49(item) for item in value.split(","))


def comma_separated_comtrade_reporters(value: str | None) -> str:
    if value is None:
        return "0"
    return ",".join(iso3_to_comtrade_reporter(item) for item in value.split(","))
