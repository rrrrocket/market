import httpx

from app.core.config import Settings
from app.services.bulk_pipeline import ComtradeLocalPipeline


def test_pipeline_http_errors_never_include_api_key(tmp_path):
    settings = Settings(
        comtrade_api_key="top-secret-key",
        comtrade_data_dir=str(tmp_path),
    )
    pipeline = ComtradeLocalPipeline(settings)
    request = httpx.Request(
        "GET",
        "https://comtradeapi.un.org/data/v1/get/C/A/HS?subscription-key=top-secret-key",
    )
    response = httpx.Response(500, request=request)
    error = httpx.HTTPStatusError("failed", request=request, response=response)
    message = pipeline._safe_error(error)
    assert message == "UN Comtrade returned HTTP 500"
    assert settings.comtrade_api_key not in message


def test_pipeline_normalizes_comtrade_annual_row(tmp_path):
    settings = Settings(comtrade_data_dir=str(tmp_path))
    pipeline = ComtradeLocalPipeline(settings)
    row = pipeline._normalize_row(
        {
            "classificationCode": "H6",
            "cmdCode": "902620",
            "period": "2025",
            "reporterISO": "USA",
            "partnerCode": 0,
            "primaryValue": 1234,
        },
        {"USA", "CHN"},
    )
    assert row is not None
    assert row["classification"] == "H6"
    assert row["period_start"].isoformat() == "2025-01-01"
    assert row["partner_iso3"] == "WLD"
    assert row["trade_value_usd"] == 1234
